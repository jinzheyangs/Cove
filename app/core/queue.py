"""ARQ 任务入队。

向量索引是异步的：
日记保存不应该等 embedding 和 Chroma，所以提交事务后再丢给 worker。

Redis 不可用时只记录告警、不阻断业务：
索引可以事后重建，日记写不进去才是大问题。

⚠️ 队列不可用时必须快速放弃：
连不上 Redis 时 create_pool 会一直等到 TCP/DNS 超时（本机实测 11 秒），
而这几个调用点全都挂在业务请求的返回路径上，用户点一下要等十几秒。
所以这里给了连接与投递各自的硬超时，并且失败后短时间内不再重试。
"""

import asyncio
import time

import structlog
from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import settings

logger = structlog.get_logger("queue")

# 连接超时 / 投递超时（秒）。超过就放弃，业务照常返回。
_CONNECT_TIMEOUT = 1.0
_ENQUEUE_TIMEOUT = 1.5
# 失败后的冷却期（秒）：这段时间内直接跳过，不再重复等超时。
_COOLDOWN = 60.0

_pool = None
_failed_at: float = 0.0


async def get_pool():
    """懒创建任务池，整个进程复用一个。"""
    global _pool
    if _pool is None:
        _pool = await asyncio.wait_for(
            create_pool(RedisSettings.from_dsn(settings.REDIS_URL)),
            timeout=_CONNECT_TIMEOUT,
        )
    return _pool


async def enqueue(function: str, *args) -> None:
    """投递一个后台任务。

    失败时只记日志。调用方都是「已经完成主业务」的场景，
    不应该因为队列不可用把请求打回，也不应该把请求拖住。
    """
    global _failed_at

    if not settings.QUEUE_ENABLED:
        return

    now = time.monotonic()
    if _failed_at and now - _failed_at < _COOLDOWN:
        return

    try:
        pool = await get_pool()
        await asyncio.wait_for(
            pool.enqueue_job(function, *args), timeout=_ENQUEUE_TIMEOUT
        )
    except Exception as exc:  # noqa: BLE001
        _failed_at = time.monotonic()
        # 连接池可能已经坏掉，丢掉它，下次重新建
        global _pool
        _pool = None
        logger.warning("queue.enqueue_failed", function=function, error=repr(exc))


# 后台投递任务持引用，防止被 GC 掉；跑完自己从集合里走
_bg_tasks: set[asyncio.Task] = set()


def enqueue_background(function: str, *args) -> None:
    """不占请求时间的投递。

    ⚠️ 即使 enqueue 有硬超时，第一次投递仍会被 Redis 连接拖住约 1 秒
    （写日记接口实测 1.1s，其中 1s 花在这），用户感受就是「点了发布卡一下」。
    所以业务侧一律用这个版本：立刻返回，投递在后台跑，失败只留日志。
    """
    if not settings.QUEUE_ENABLED:
        return
    task = asyncio.create_task(enqueue(function, *args), name=f"q_{function}")
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)


async def close_pool() -> None:
    global _pool
    if _pool is None:
        return
    try:
        await _pool.aclose()
    except AttributeError:
        await _pool.close()
    _pool = None
