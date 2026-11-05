"""滑动窗口限流：额度、被拒请求不占名额、窗口滑动、计数与重置。

这些用例需要真实 Redis（Lua 脚本无法用内存假实现可靠模拟）。
本地先 docker compose up -d redis；连不上会自动 skip。
"""

import asyncio
import os

import pytest_asyncio
from redis.asyncio import Redis

from app.core.config import settings
from app.core.ratelimit import RateLimiter

TEST_REDIS_URL = os.getenv("TEST_REDIS_URL", "redis://localhost:56379/15")


@pytest_asyncio.fixture
async def limiter(monkeypatch):
    # 测试默认关闭限流，这里单独打开
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)

    client = Redis.from_url(
        TEST_REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=2,
    )
    try:
        await client.ping()
    except Exception:
        await client.aclose()
        raise RuntimeError(
            "需要 Redis：先执行 docker compose up -d redis"
        ) from None

    # 用独立的 db 15，避免污染业务数据
    await client.flushdb()
    yield RateLimiter(client)
    await client.aclose()


async def test_allows_up_to_limit_then_rejects(limiter):
    for _ in range(3):
        assert await limiter.hit("k", 3, 60) is True

    assert await limiter.hit("k", 3, 60) is False


async def test_rejected_requests_do_not_consume_quota(limiter):
    for _ in range(3):
        await limiter.hit("k", 3, 60)

    # 连续被拒多次，窗口内仍然只算 3 个
    assert await limiter.hit("k", 3, 60) is False
    assert await limiter.hit("k", 3, 60) is False
    assert await limiter.count("k", 60) == 3


async def test_window_slides(limiter):
    assert await limiter.hit("k", 1, 1) is True
    assert await limiter.hit("k", 1, 1) is False

    # 超过窗口后，旧记录被清理，重新放行
    await asyncio.sleep(1.1)
    assert await limiter.hit("k", 1, 1) is True


async def test_count_and_reset(limiter):
    await limiter.hit("k", 10, 60)
    await limiter.hit("k", 10, 60)

    assert await limiter.count("k", 60) == 2

    await limiter.reset("k")
    assert await limiter.count("k", 60) == 0


async def test_keys_are_isolated(limiter):
    await limiter.hit("a", 1, 60)

    assert await limiter.hit("b", 1, 60) is True
