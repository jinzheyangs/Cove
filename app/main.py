from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.core.config import settings
from app.core.db import engine
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.modules.bills.router import router as bills_router
from app.modules.coin_applies.router import router as coin_applies_router
from app.modules.coins.router import router as coins_router
from app.modules.conflicts.router import router as conflicts_router
from app.modules.couples.router import router as couples_router
from app.modules.daily.router import router as daily_router
from app.modules.diaries.router import router as diaries_router
from app.modules.inquiries.router import router as inquiries_router
from app.modules.mall.router import router as mall_router
from app.modules.secrets.router import router as secrets_router
from app.modules.simta.router import router as simta_router
from app.modules.todos.router import router as todos_router
from app.modules.users.router import auth_router, users_router

API_PREFIX = "/api/v1"

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(title=settings.APP_NAME, version="0.1.0", lifespan=lifespan)
app.add_middleware(RequestContextMiddleware)
register_exception_handlers(app)

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
app.include_router(conflicts_router, prefix=API_PREFIX)
app.include_router(inquiries_router, prefix=API_PREFIX)
app.include_router(daily_router, prefix=API_PREFIX)
app.include_router(simta_router, prefix=API_PREFIX)


@app.get("/health")
async def health() -> dict:
    return {"code": 0, "message": "success", "data": {"status": "ok"}}


@app.get("/health/db")
async def health_db() -> dict:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"code": 0, "message": "success", "data": {"db": "ok"}}
