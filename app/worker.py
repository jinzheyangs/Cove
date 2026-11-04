"""ARQ 后台任务 worker。

启动方式：arq app.worker.WorkerSettings
"""

from arq.connections import RedisSettings

from app.core.config import settings


async def ping(ctx: dict) -> str:
    """最小连通性任务。"""
    return "pong"


class WorkerSettings:
    functions = [ping]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
