"""应用入口：装配中间件、路由、异常处理和可观测性。

这里的顺序很重要，改动时注意：
1. configure_logging() 必须最早，后续初始化日志才有格式
2. 中间件后添加的在外层，RequestContext 必须最外层
3. setup_tracing 必须在 app 和路由都配置好之后调用
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text

from app.core.config import settings
from app.core.crypto import ensure_configured
from app.core.db import engine
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import (
    RateLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.tracing import setup_tracing
from app.modules.audit.router import router as audit_router
from app.modules.bills.router import router as bills_router
from app.modules.coin_applies.router import router as coin_applies_router
from app.modules.coins.router import router as coins_router
from app.modules.conflicts.router import router as conflicts_router
from app.modules.couples.router import router as couples_router
from app.modules.daily.router import router as daily_router
from app.modules.diaries.router import router as diaries_router
from app.modules.inquiries.router import router as inquiries_router
from app.modules.mall.router import router as mall_router
from app.modules.notifications.router import router as notifications_router
from app.modules.privacy.router import router as privacy_router
from app.modules.secrets.router import router as secrets_router
from app.modules.simta.router import router as simta_router
from app.modules.todos.router import router as todos_router
from app.modules.users.router import auth_router, users_router

# 所有业务接口统一带版本前缀，方便以后做不兼容升级
API_PREFIX = "/api/v1"

# 必须在创建 app 之前配置，否则启动阶段的日志没有格式
configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动和关闭时的钩子。

    启动：生产环境检查加密密钥，缺失则直接拒绝启动（fail fast）
    关闭：释放数据库连接池
    """
    ensure_configured()
    yield
    await engine.dispose()


app = FastAPI(title=settings.APP_NAME, version="0.1.0", lifespan=lifespan)

# 中间件顺序：后添加的在外层。
# 实际执行顺序从外到内是 RequestContext -> RateLimit -> SecurityHeaders -> CORS。
# RequestContext 最外层，保证限流等后续日志也带 request_id。
if settings.cors_origins:
    # 只有配置了来源才启用 CORS；手机 App 不发送 Origin，不需要
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestContextMiddleware)

# 统一异常格式：{code, message, data}
register_exception_handlers(app)

# ---- 业务路由 ----------------------------------------------------------
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(users_router, prefix=API_PREFIX)
app.include_router(couples_router, prefix=API_PREFIX)
app.include_router(coins_router, prefix=API_PREFIX)
app.include_router(secrets_router, prefix=API_PREFIX)
app.include_router(coin_applies_router, prefix=API_PREFIX)
app.include_router(mall_router, prefix=API_PREFIX)
app.include_router(diaries_router, prefix=API_PREFIX)
app.include_router(todos_router, prefix=API_PREFIX)
app.include_router(bills_router, prefix=API_PREFIX)
app.include_router(audit_router, prefix=API_PREFIX)
app.include_router(conflicts_router, prefix=API_PREFIX)
app.include_router(inquiries_router, prefix=API_PREFIX)
app.include_router(daily_router, prefix=API_PREFIX)
app.include_router(simta_router, prefix=API_PREFIX)
app.include_router(privacy_router, prefix=API_PREFIX)
app.include_router(notifications_router, prefix=API_PREFIX)


# 必须在 app 和路由都配置好之后接入，否则部分路由不会被插桩
setup_tracing(app, engine)


# ---- 运维接口 ----------------------------------------------------------
@app.get("/health")
async def health() -> dict:
    """进程存活检查。不访问数据库，用于负载均衡/容器探活。"""
    return {"code": 0, "message": "success", "data": {"status": "ok"}}


@app.get("/health/db")
async def health_db() -> dict:
    """数据库连通性检查。数据库不可用时这里会抛 500。"""
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"code": 0, "message": "success", "data": {"db": "ok"}}


@app.get("/metrics")
async def metrics(request: Request) -> Response:
    """Prometheus 指标端点。

    建议只在内网暴露；如果必须通过公网访问，
    设置 METRICS_TOKEN 并要求请求带上 X-Metrics-Token。
    """
    if settings.METRICS_TOKEN and (
        request.headers.get("X-Metrics-Token") != settings.METRICS_TOKEN
    ):
        return Response(status_code=403)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
