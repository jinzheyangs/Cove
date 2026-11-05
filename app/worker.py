"""ARQ 后台任务 worker。

启动方式：arq app.worker.WorkerSettings
"""

import structlog
from arq import cron
from arq.connections import RedisSettings
from opentelemetry import trace

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.logging import configure_logging
from app.core.metrics import COIN_RECONCILE_MISMATCHES
from app.core.tracing import setup_tracing
from app.modules.coins import service as coin_service
from app.modules.secrets import service as secret_service

configure_logging()
setup_tracing()
logger = structlog.get_logger("worker")
tracer = trace.get_tracer("cove.worker")


async def ping(ctx: dict) -> str:
    """最小连通性任务。"""
    return "pong"


async def reconcile_coins(ctx: dict) -> int:
    """每天对账一次：余额缓存必须和流水一致。"""
    with tracer.start_as_current_span("worker.reconcile_coins"):
        async with SessionLocal() as session:
            mismatches = await coin_service.reconcile(session)

        COIN_RECONCILE_MISMATCHES.set(len(mismatches))
        if mismatches:
            logger.error("金币对账不一致 (user_id, cached, expected): %s", mismatches)
        else:
            logger.info("金币对账通过")
        return len(mismatches)


async def purge_burned_secrets(ctx: dict) -> int:
    """燃尽期结束后，把阅后即焚的秘密内容清空。"""
    with tracer.start_as_current_span("worker.purge_burned_secrets"):
        async with SessionLocal() as session:
            count = await secret_service.purge_burned(session)

        logger.info("清理燃尽秘密 %d 条", count)
        return count


class WorkerSettings:
    functions = [ping]
    cron_jobs = [
        cron(reconcile_coins, hour=3, minute=17),
        cron(purge_burned_secrets, hour=3, minute=41),
    ]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
