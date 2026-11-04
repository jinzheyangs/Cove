from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.core.config import settings
from app.core.db import engine
from app.core.errors import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(title=settings.APP_NAME, version="0.1.0", lifespan=lifespan)
register_exception_handlers(app)


@app.get("/health")
async def health() -> dict:
    return {"code": 0, "message": "success", "data": {"status": "ok"}}


@app.get("/health/db")
async def health_db() -> dict:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"code": 0, "message": "success", "data": {"db": "ok"}}
