"""ARQ 后台任务 worker。

启动方式：arq app.worker.WorkerSettings
"""

import logging

from arq import cron
from arq.connections import RedisSettings

from app.core.config import settings
from app.core.db import SessionLocal
from app.modules.coins import service as coin_service

logger = logging.getLogger(__name__)


async def ping(ctx: dict) -> str:
    """最小连通性任务。"""
    return "pong"


async def reconcile_coins(ctx: dict) -> int:
    """每天对账一次：余额缓存必须和流水一致。"""
    async with SessionLocal() as session:
        mismatches = await coin_service.reconcile(session)

    if mismatches:
        logger.error("金币对账不一致 (user_id, cached, expected): %s", mismatches)
    else:
        logger.info("金币对账通过")
    return len(mismatches)


class WorkerSettings:
    functions = [ping]
    cron_jobs = [cron(reconcile_coins, hour=3, minute=17)]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
