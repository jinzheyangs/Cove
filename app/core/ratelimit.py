"""基于 Redis 的固定窗口限流。

设计原则：Redis 不可用时**放行**（fail open）。
限流是为了防滥用，不应该因为缓存挂了把整个服务拖死。
"""

import structlog
from redis.asyncio import Redis

from app.core.config import settings
from app.core.redis import get_redis

logger = structlog.get_logger("ratelimit")


class RateLimiter:
    def __init__(self, client: Redis) -> None:
        self.client = client

    async def hit(self, key: str, limit: int, window: int) -> bool:
        """计数并判断是否放行。Redis 故障时放行。"""
        if not settings.RATE_LIMIT_ENABLED:
            return True
        try:
            count = await self.client.incr(key)
            if count == 1:
                await self.client.expire(key, window)
            return count <= limit
        except Exception as exc:  # noqa: BLE001 - 缓存故障不应影响业务
            logger.warning("ratelimit.unavailable", error=repr(exc))
            return True

    async def count(self, key: str) -> int:
        if not settings.RATE_LIMIT_ENABLED:
            return 0
        try:
            value = await self.client.get(key)
            return int(value or 0)
        except Exception as exc:  # noqa: BLE001
            logger.warning("ratelimit.unavailable", error=repr(exc))
            return 0

    async def reset(self, key: str) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return
        try:
            await self.client.delete(key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("ratelimit.unavailable", error=repr(exc))


def get_limiter() -> RateLimiter:
    return RateLimiter(get_redis())
