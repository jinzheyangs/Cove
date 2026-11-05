"""HTTP 中间件。

注册顺序在 app/main.py，注意：**后添加的在外层**。
当前从内到外是：
    SecurityHeaders -> RateLimit -> RequestContext
这样 RequestContext 最先执行，后续所有日志（包括限流日志）都能带上 request_id。
"""

import time
import uuid

import structlog
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.config import settings
from app.core.metrics import REQUEST_COUNT, REQUEST_LATENCY
from app.core.ratelimit import get_limiter

logger = structlog.get_logger("http")

# 健康和指标接口不参与限流，否则 Prometheus 每 15 秒抓取会被误伤
_SKIP_RATE_LIMIT = {"/health", "/health/db", "/metrics"}


class RequestContextMiddleware(BaseHTTPMiddleware):
    """请求上下文：request_id、耗时、指标、访问日志。

    设计要点：
    - 优先复用调用方传来的 X-Request-ID，便于前端把错误 ID 报给后端
    - 把 request_id / path / IP 写进 structlog 上下文，后续日志自动携带
    - 指标用「路由模板」而不是真实路径，避免 /secrets/1 和 /secrets/2 各开一条时间序列
    - 刻意不记录请求体：这里的数据大多是隐私内容
    """

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex

        # 每个请求开始前清空，防止上一个请求的上下文泄漏到当前请求
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )

        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # 未捕获异常也要计入指标，否则 5xx 告警会漏
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            route = request.scope.get("route")
            path = getattr(route, "path", request.url.path)
            REQUEST_COUNT.labels(request.method, path, "500").inc()
            REQUEST_LATENCY.labels(request.method, path).observe(duration_ms / 1000)
            logger.exception("request.failed", duration_ms=duration_ms)
            raise

        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        # 路由模板（如 /api/v1/secrets/{secret_id}），保证指标基数可控
        route = request.scope.get("route")
        path = getattr(route, "path", request.url.path)
        REQUEST_COUNT.labels(request.method, path, str(response.status_code)).inc()
        REQUEST_LATENCY.labels(request.method, path).observe(duration_ms / 1000)

        # 回传给客户端，前端报错时可以带上这个 ID
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request.completed",
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """给所有响应补上基础安全头。

    这些头主要防浏览器侧的低级攻击；手机 App 用不到，
    但成本为零，Web 端和未来可能的小程序端会受益。
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # 禁止浏览器猜测 Content-Type
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        # 禁止被 iframe 嵌入，防点击劫持
        response.headers.setdefault("X-Frame-Options", "DENY")
        # 跨站跳转时不带来源路径，减少隐私泄露
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        # 这个产品不需要定位/麦克风/摄像头权限
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        # HSTS 只在生产环境开：本地 http 开了会把浏览器锁死
        if settings.ENV == "prod":
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """按 IP 的粗粒度限流。

    分三档：
    - auth：撞库成本最低，限得最严
    - ai：模型调用又慢又贵，单独一档
    - global：其余接口

    真正的登录失败锁定在 users/service.py 里按手机号做，
    这里只是 IP 维度的第一道闸。
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not settings.RATE_LIMIT_ENABLED or path in _SKIP_RATE_LIMIT:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        limit = settings.RATE_LIMIT_REQUESTS
        window = settings.RATE_LIMIT_WINDOW_SECONDS
        bucket = "global"

        if path.startswith("/api/v1/auth"):
            limit = settings.AUTH_RATE_LIMIT_REQUESTS
            bucket = "auth"
        elif path.startswith("/api/v1/inquiries") or path.startswith("/api/v1/sim-ta"):
            limit = settings.AI_RATE_LIMIT_REQUESTS
            bucket = "ai"

        allowed = await get_limiter().hit(
            f"rl:{bucket}:{client_ip}", limit, window
        )
        if not allowed:
            logger.warning("rate_limit.exceeded", bucket=bucket, client_ip=client_ip)
            # 这里直接返回，不走异常处理器：限流发生在进入路由之前
            return JSONResponse(
                status_code=429,
                content={
                    "code": 429,
                    "message": "请求太频繁了，请稍后再试",
                    "data": None,
                },
            )

        return await call_next(request)
