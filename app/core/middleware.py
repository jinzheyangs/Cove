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

_SKIP_RATE_LIMIT = {"/health", "/health/db", "/metrics"}


class RequestContextMiddleware(BaseHTTPMiddleware):
    """给每个请求分配 request_id，并记录耗时。

    - 优先复用调用方传来的 X-Request-ID
    - 写进 structlog context，之后所有日志自动带上
    - 响应头返回，前端报错时可以带上这个 ID

    刻意不记录请求体：这里的数据大多是隐私内容。
    """

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex

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
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            route = request.scope.get("route")
            path = getattr(route, "path", request.url.path)
            REQUEST_COUNT.labels(request.method, path, "500").inc()
            REQUEST_LATENCY.labels(request.method, path).observe(duration_ms / 1000)
            logger.exception("request.failed", duration_ms=duration_ms)
            raise

        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        route = request.scope.get("route")
        path = getattr(route, "path", request.url.path)
        REQUEST_COUNT.labels(request.method, path, str(response.status_code)).inc()
        REQUEST_LATENCY.labels(request.method, path).observe(duration_ms / 1000)

        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request.completed",
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        if settings.ENV == "prod":
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """按 IP 做粗粒度限流；登录接口更严，AI 接口单独一档。"""

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
            return JSONResponse(
                status_code=429,
                content={
                    "code": 429,
                    "message": "请求太频繁了，请稍后再试",
                    "data": None,
                },
            )

        return await call_next(request)
