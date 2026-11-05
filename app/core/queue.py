"""ARQ 任务入队。

向量索引是异步的：
日记保存不应该等 embedding 和 Chroma，所以提交事务后再丢给 worker。

Redis 不可用时只记录告警、不阻断业务：
索引可以事后重建，日记写不进去才是大问题。
"""

import structlog
from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import settings

logger = structlog.get_logger("queue")

_pool = None


async def get_pool():
    """懒创建任务池，整个进程复用一个。"""
    global _pool
    if _pool is None:
        _pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    return _pool


async def enqueue(function: str, *args) -> None:
    """投递一个后台任务。

    失败时只记日志。调用方都是「已经完成主业务」的场景，
    不应该因为队列不可用把请求打回。
    """
    if not settings.QUEUE_ENABLED:
        return

    try:
        pool = await get_pool()
        await pool.enqueue_job(function, *args)
    except Exception as exc:  # noqa: BLE001
        logger.warning("queue.enqueue_failed", function=function, error=repr(exc))


async def close_pool() -> None:
    """应用退出时关闭连接池。"""
    global _pool
    if _pool is None:
        return
    try:
        await _pool.aclose()
    except AttributeError:
        await _pool.close()
    _pool = None
