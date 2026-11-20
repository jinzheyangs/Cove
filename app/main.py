"""应用入口：装配中间件、路由、异常处理和可观测性。

这里的顺序很重要，改动时注意：
1. configure_logging() 必须最早，后续初始化日志才有格式
2. 中间件后添加的在外层，RequestContext 必须最外层
3. setup_tracing 必须在 app 和路由都配置好之后调用
"""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
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
from app.core.redis import close_redis
from app.core.storage import validate_storage_config
from app.core.tracing import setup_tracing
from app.modules.agent.router import router as agent_router
from app.modules.anniversaries.router import router as anniversaries_router
from app.modules.bills.router import router as bills_router
from app.modules.coin_applies.router import router as coin_applies_router
from app.modules.coins.router import router as coins_router
from app.modules.couples.router import router as couples_router
from app.modules.daily.router import router as daily_router
from app.modules.diaries.router import router as diaries_router
from app.modules.mall.router import router as mall_router
from app.modules.mood.router import router as mood_router
from app.modules.notifications.router import router as notifications_router
from app.modules.privacy.router import router as privacy_router
from app.modules.secrets.router import router as secrets_router
from app.modules.simta.router import router as simta_router
from app.modules.todos.router import router as todos_router
from app.modules.uploads.router import router as uploads_router
from app.modules.users.router import auth_router, users_router

# 所有业务接口统一带版本前缀，方便以后做不兼容升级
API_PREFIX = "/api/v1"

# 必须在创建 app 之前配置，否则启动阶段的日志没有格式
configure_logging()


async def _warm_ai() -> None:
    """后台预热向量库连接。失败只记一笔，不影响任何请求。"""
    from app.modules.ai import vectorstore

    await asyncio.to_thread(vectorstore.warm)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动和关闭时的钩子。

    启动：生产环境检查加密密钥，缺失则直接拒绝启动（fail fast）
    关闭：释放数据库连接池和 Redis 连接
    """
    ensure_configured()
    validate_storage_config()
    # 后台预热向量库：不解阻塞启动，只为第一句「模拟TA」少等一次建连
    warm_task = asyncio.create_task(_warm_ai())
    yield
    warm_task.cancel()
    await close_redis()
    await close_pool()
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

# 本地存储模式把上传目录挂成静态资源，方便开发时直接预览图片。
# 生产环境用 OSS，不会走到这里。
if settings.STORAGE_BACKEND == "local":
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

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
app.include_router(daily_router, prefix=API_PREFIX)
app.include_router(mood_router, prefix=API_PREFIX)
app.include_router(anniversaries_router, prefix=API_PREFIX)
app.include_router(simta_router, prefix=API_PREFIX)
app.include_router(privacy_router, prefix=API_PREFIX)
app.include_router(notifications_router, prefix=API_PREFIX)
app.include_router(uploads_router, prefix=API_PREFIX)
app.include_router(agent_router, prefix=API_PREFIX)


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


# ---- 前端同源托管 ----------------------------------------------------------
# `cd frontend && npm run build` 之后，直接访问 http://localhost:8000/ 就是完整 App。
# 路径相对仓库根解析，不依赖 uvicorn 的启动目录；dist 不存在时整段自动跳过，
# 后端仍可作为纯 API 服务运行（开发时用 Vite 代理 /api 与 /uploads）。
# 这一段必须排在所有业务路由之后：catch-all 不能抢掉 /api、/uploads、/docs 等。
_FRONTEND_DIST = (Path(__file__).resolve().parent.parent / settings.FRONTEND_DIST).resolve()

if _FRONTEND_DIST.is_dir():
    _assets = _FRONTEND_DIST / "assets"
    if _assets.is_dir():
        app.mount("/assets", StaticFiles(directory=_assets), name="frontend-assets")

    @app.get("/{spa_path:path}", include_in_schema=False)
    async def spa_fallback(spa_path: str) -> Response:
        """SPA 只有一个入口；未知的非 API 路径一律回 index.html。"""
        if spa_path.startswith(
            ("api/", "uploads/", "assets/", "health", "metrics", "docs", "redoc", "openapi.json")
        ):
            return Response(status_code=404)
        index = _FRONTEND_DIST / "index.html"
        if not index.is_file():
            return Response(status_code=404)
        return FileResponse(index, media_type="text/html")
