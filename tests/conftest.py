import os

# 测试不依赖 Redis：必须在导入 app 之前关掉限流
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

import asyncpg
import pytest_asyncio
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.modules  # noqa: F401  确保所有模型注册到 Base.metadata
from app.core.db import Base

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://cove:cove_dev_pass@localhost:55432/cove_test",
)

_db_ready = False


async def _ensure_database() -> None:
    """测试库不存在时自动创建，让 CI 和本地都能直接跑。"""
    global _db_ready
    if _db_ready:
        return

    url = make_url(TEST_DATABASE_URL)
    db_name = url.database
    admin_url = url.set(drivername="postgresql", database="postgres")
    conn = await asyncpg.connect(admin_url.render_as_string(hide_password=False))
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", db_name
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await conn.close()

    _db_ready = True


@pytest_asyncio.fixture
async def engine():
    await _ensure_database()
    eng = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def session(session_factory):
    async with session_factory() as s:
        yield s
