"""ARQ 后台任务 worker。

启动方式：
    arq app.worker.WorkerSettings

当前只有两个定时任务：
- 每天 03:17 金币对账
- 每天 03:41 清理燃尽期已过的秘密内容
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
from app.modules.agent import service as agent_service
from app.modules.ai import indexing
from app.modules.coins import service as coin_service
from app.modules.secrets import service as secret_service

# worker 是独立进程，日志和追踪都要单独初始化
configure_logging()
setup_tracing()
logger = structlog.get_logger("worker")
tracer = trace.get_tracer("cove.worker")


async def ping(ctx: dict) -> str:
    """最小连通性任务，用于验证 worker 和 Redis 正常。"""
    return "pong"


async def reconcile_coins(ctx: dict) -> int:
    """金币对账。

    从流水重算每个账户的应有余额，和缓存余额比对。
    结果写入 Prometheus 指标，告警规则见 deploy/prometheus/alerts.yml。

    Returns:
        不一致的账户数量，0 表示全部正确。
    """
    with tracer.start_as_current_span("worker.reconcile_coins"):
        # cron 任务没有请求上下文，需要自己开会话
        async with SessionLocal() as session:
            mismatches = await coin_service.reconcile(session)

        COIN_RECONCILE_MISMATCHES.set(len(mismatches))
        if mismatches:
            # 只记录 id 和数字，不打印任何隐私内容
            logger.error("金币对账不一致 (user_id, cached, expected): %s", mismatches)
        else:
            logger.info("金币对账通过")
        return len(mismatches)


async def purge_burned_secrets(ctx: dict) -> int:
    """清理燃尽期已过的秘密内容。

    摘取时只标记 burned，内容保留 24 小时；
    这里负责把超过宽限期的正文清空。

    Returns:
        被清理的记录数。
    """
    with tracer.start_as_current_span("worker.purge_burned_secrets"):
        async with SessionLocal() as session:
            count = await secret_service.purge_burned(session)

        logger.info("清理燃尽秘密 %d 条", count)
        return count


async def cleanup_agent_conversations(ctx: dict) -> int:
    """删除过期会话和消息，返回清理数量。"""
    with tracer.start_as_current_span("worker.cleanup_agent_conversations"):
        async with SessionLocal() as session:
            count = await agent_service.cleanup_expired(session)

        logger.info("清理过期会话 %d 个", count)
        return count


async def index_diary(ctx: dict, diary_id: int) -> None:
    """重建一篇日记的向量索引。"""
    with tracer.start_as_current_span("worker.index_diary"):
        async with SessionLocal() as session:
            await indexing.index_diary(session, diary_id)


async def delete_diary_vectors(ctx: dict, diary_id: int) -> None:
    """删除一篇日记的向量索引。"""
    with tracer.start_as_current_span("worker.delete_diary_vectors"):
        async with SessionLocal() as session:
            await indexing.delete_diary_vectors(session, diary_id)


async def index_review(ctx: dict, review_id: int) -> None:
    """重建一份复盘的向量索引。"""
    with tracer.start_as_current_span("worker.index_review"):
        async with SessionLocal() as session:
            await indexing.index_review(session, review_id)


async def delete_user_vectors(ctx: dict, couple_id: int | None, user_id: int) -> None:
    """删除某个用户的向量。

    撤销模拟TA 授权时传 couple_id；
    注销账号时 couple_id 为空，按用户全局删除。
    """
    with tracer.start_as_current_span("worker.delete_user_vectors"):
        async with SessionLocal() as session:
            await indexing.delete_user_vectors(session, couple_id, user_id)


class WorkerSettings:
    """ARQ 的启动配置。

    注意：cron 任务在每个 worker 实例上都会运行。
    如果以后把 worker 扩成多实例，需要把定时任务拆到单独进程，
    否则会对账多次、清理多次（虽然幂等，但没必要）。
    """

    functions = [
        ping,
        index_diary,
        delete_diary_vectors,
        index_review,
        delete_user_vectors,
    ]
    # 错开整点执行，避免和其他系统的定时任务撞车
    cron_jobs = [
        cron(reconcile_coins, hour=3, minute=17),
        cron(purge_burned_secrets, hour=3, minute=41),
        cron(cleanup_agent_conversations, hour=4, minute=7),
    ]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
