from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.core.config import settings
from app.core.db import engine
from app.core.errors import register_exception_handlers
from app.modules.couples.router import router as couples_router
from app.modules.users.router import auth_router, users_router

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(title=settings.APP_NAME, version="0.1.0", lifespan=lifespan)
register_exception_handlers(app)

app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(users_router, prefix=API_PREFIX)
app.include_router(couples_router, prefix=API_PREFIX)


@app.get("/health")
async def health() -> dict:
    return {"code": 0, "message": "success", "data": {"status": "ok"}}


@app.get("/health/db")
async def health_db() -> dict:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"code": 0, "message": "success", "data": {"db": "ok"}}
