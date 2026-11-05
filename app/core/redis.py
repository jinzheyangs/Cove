"""Redis 客户端。

只做一件事：进程内复用同一个异步连接池。
限流、登录失败计数都走这里。
"""

from redis.asyncio import Redis

from app.core.config import settings

# 模块级单例。Redis 客户端本身带连接池，创建一次即可
_client: Redis | None = None


def get_redis() -> Redis:
    """返回全局客户端，首次调用时创建。

    - decode_responses=True：取回来就是 str，不用到处 decode
    - 超时设成 1 秒：Redis 故障时尽快失败，让调用方走 fail open
    """
    global _client
    if _client is None:
        _client = Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
    return _client


async def close_redis() -> None:
    """关闭连接池。应用退出时调用，避免连接泄漏。"""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
