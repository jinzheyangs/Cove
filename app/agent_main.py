"""独立 AI 服务入口。

只挂载 /api/v1/agent，方便单独部署和扩缩容。
业务接口仍由 app.main 提供。

部署时可以：
- 用 nginx 把 /api/v1/agent 转发到本服务
- 或者直接让客户端连接 8100 端口

两个服务共享同一个 PG、Redis、Chroma。
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
from app.core.queue import close_pool
from app.core.storage import validate_storage_config
from app.core.tracing import setup_tracing
from app.modules.agent.router import router as agent_router

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_configured()
    validate_storage_config()
    yield
    await close_pool()
    await engine.dispose()


app = FastAPI(
    title=f"{settings.APP_NAME} Agent", version="0.1.0", lifespan=lifespan
)

if settings.cors_origins:
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

register_exception_handlers(app)
app.include_router(agent_router, prefix="/api/v1")
setup_tracing(app, engine)


@app.get("/health")
async def health() -> dict:
    return {"code": 0, "message": "success", "data": {"status": "ok"}}


@app.get("/health/db")
async def health_db() -> dict:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"code": 0, "message": "success", "data": {"db": "ok"}}


@app.get("/metrics")
async def metrics(request: Request) -> Response:
    if settings.METRICS_TOKEN and (
        request.headers.get("X-Metrics-Token") != settings.METRICS_TOKEN
    ):
        return Response(status_code=403)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
