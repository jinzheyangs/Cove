"""基于 Redis 的固定窗口限流。

为什么是固定窗口而不是滑动窗口：
实现只有 INCR + EXPIRE 两个命令，够用且不会成为性能瓶颈。
边界处可能短暂放过 2 倍流量，对这个规模的产品可以接受。

设计原则：Redis 不可用时**放行**（fail open）。
限流是为了防滥用，不应该因为缓存挂了把整个服务拖死。
"""

import structlog
from redis.asyncio import Redis

from app.core.config import settings
from app.core.redis import get_redis

logger = structlog.get_logger("ratelimit")


class RateLimiter:
    """封装 Redis 的计数器操作。

    传入 client 而不是在内部创建，方便测试时注入假实现。
    """

    def __init__(self, client: Redis) -> None:
        self.client = client

    async def hit(self, key: str, limit: int, window: int) -> bool:
        """计数 +1，并判断是否仍在额度内。

        Returns:
            True 表示放行，False 表示超限。

        第一次命中时设置过期时间，之后窗口内不再续期，
        这样窗口是固定的，不会因为持续请求而无限延长。
        """
        if not settings.RATE_LIMIT_ENABLED:
            return True
        try:
            count = await self.client.incr(key)
            if count == 1:
                await self.client.expire(key, window)
            return count <= limit
        except Exception as exc:  # noqa: BLE001 - 缓存故障不应影响业务
            # fail open：记录告警，但放行
            logger.warning("ratelimit.unavailable", error=repr(exc))
            return True

    async def count(self, key: str) -> int:
        """读取当前计数，不增加。

        登录失败锁定时用它先检查，避免每次登录都白白 +1。
        """
        if not settings.RATE_LIMIT_ENABLED:
            return 0
        try:
            value = await self.client.get(key)
            return int(value or 0)
        except Exception as exc:  # noqa: BLE001
            logger.warning("ratelimit.unavailable", error=repr(exc))
            return 0

    async def reset(self, key: str) -> None:
        """清空计数。登录成功后调用，把失败次数归零。"""
        if not settings.RATE_LIMIT_ENABLED:
            return
        try:
            await self.client.delete(key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("ratelimit.unavailable", error=repr(exc))


def get_limiter() -> RateLimiter:
    """每次返回轻量包装对象，底层 Redis 客户端是全局复用的。"""
    return RateLimiter(get_redis())
