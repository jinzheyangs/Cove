"""ARQ 后台任务 worker。

启动方式：
    arq app.worker.WorkerSettings

定时任务：
- 每天 03:17 金币对账
- 每天 04:07 清理过期 Agent 会话
- 每天 04:17 过期未确认的 Agent 动作
- 每天 04:27 清理过期刷新令牌
- 每天 04:37 补齐对话记忆索引
- 每小时第 7 分 向量对账（补回 Chroma 丢的数据）
"""

from datetime import UTC, datetime, timedelta

import structlog
from arq import cron
from arq.connections import RedisSettings
from opentelemetry import trace
from sqlalchemy import delete, or_, select

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.logging import configure_logging
from app.core.metrics import COIN_RECONCILE_MISMATCHES
from app.core.tracing import setup_tracing
from app.modules.agent import actions as agent_actions
from app.modules.agent import service as agent_service
from app.modules.agent.models import AgentConversation
from app.modules.ai import indexing
from app.modules.coins import service as coin_service
from app.modules.users.models import RefreshToken

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


async def expire_agent_actions(ctx: dict) -> int:
    """把超时未确认的动作标记为 expired。"""
    with tracer.start_as_current_span("worker.expire_agent_actions"):
        async with SessionLocal() as session:
            count = await agent_actions.expire_pending(session)

        logger.info("过期 Agent 动作 %d 个", count)
        return count


async def cleanup_agent_conversations(ctx: dict) -> int:
    """删除过期会话和消息，返回清理数量。"""
    with tracer.start_as_current_span("worker.cleanup_agent_conversations"):
        async with SessionLocal() as session:
            count = await agent_service.cleanup_expired(session)

        logger.info("清理过期会话 %d 个", count)
        return count


async def cleanup_refresh_tokens(ctx: dict) -> int:
    """清理过期和已吊销的刷新令牌记录。

    每次刷新都会把旧记录标成 revoked 并插入一条新的，
    不清的话单用户一年就能堆上万行。保留 7 天，够排查「刚被登出」的情况。
    """
    cutoff = datetime.now(UTC) - timedelta(days=7)
    with tracer.start_as_current_span("worker.cleanup_refresh_tokens"):
        async with SessionLocal() as session:
            result = await session.execute(
                delete(RefreshToken).where(
                    or_(
                        RefreshToken.expires_at < cutoff,
                        RefreshToken.revoked_at < cutoff,
                    )
                )
            )
            await session.commit()
            count = result.rowcount or 0

        logger.info("清理刷新令牌 %d 条", count)
        return count


async def reconcile_vectors(ctx: dict) -> int:
    """每天和 Chroma 对一次账：补回丢失的向量、清掉残留和孤儿。

    Chroma 丢数据时不会报错，表现只是「Ta 想不起你说过的话」，
    所以必须有个任务主动发现并修，不能靠人手动重建。
    """
    with tracer.start_as_current_span("worker.reconcile_vectors"):
        async with SessionLocal() as session:
            result = await indexing.reconcile_vectors(session)

        logger.info(
            "向量对账：补回 %d，清残留 %d，删孤儿 %d",
            result["repaired"],
            result["stale"],
            result["orphans"],
        )
        return result["repaired"]


async def index_diary(ctx: dict, diary_id: int) -> None:
    """重建一篇日记的向量索引。"""
    with tracer.start_as_current_span("worker.index_diary"):
        async with SessionLocal() as session:
            await indexing.index_diary(session, diary_id)


async def index_conversation_memories(ctx: dict, conversation_id: int) -> None:
    """把一次会话切块存成长期记忆，并建向量索引。

    由「离开模拟Ta 页面」触发；失败只记日志，不重试到打爆上游。
    """
    with tracer.start_as_current_span("worker.index_conversation_memories"):
        async with SessionLocal() as session:
            try:
                count = await indexing.index_chat_memories(session, conversation_id)
            except Exception as exc:  # noqa: BLE001 - 记忆失败不该影响用户聊天
                await session.rollback()
                logger.warning(
                    "worker.memory_failed", conversation_id=conversation_id, error=repr(exc)
                )
                return

        logger.info("会话记忆入库 %d 块 (conversation_id=%d)", count, conversation_id)


async def delete_diary_vectors(ctx: dict, diary_id: int) -> None:
    """删除一篇日记的向量索引。"""
    with tracer.start_as_current_span("worker.delete_diary_vectors"):
        async with SessionLocal() as session:
            await indexing.delete_diary_vectors(session, diary_id)


async def delete_user_vectors(ctx: dict, couple_id: int | None, user_id: int) -> None:
    """删除某个用户的向量。

    撤销模拟TA 授权时传 couple_id；
    注销账号时 couple_id 为空，按用户全局删除。
    """
    with tracer.start_as_current_span("worker.delete_user_vectors"):
        async with SessionLocal() as session:
            await indexing.delete_user_vectors(session, couple_id, user_id)


async def index_all_memories(ctx: dict) -> int:
    """每天兜底扫一遍：有消息的会话都重新切块入库。

    页面离开时已经触发过一次，这里只补「没触发成功的」
    （杀进程、断网）。块内容没变的不会重新 embedding。
    """
    with tracer.start_as_current_span("worker.index_all_memories"):
        async with SessionLocal() as session:
            ids = list(
                await session.scalars(
                    select(AgentConversation.id).where(
                        AgentConversation.persist.is_(True)
                    )
                )
            )
            total = 0
            for conversation_id in ids:
                try:
                    total += await indexing.index_chat_memories(session, conversation_id)
                except Exception as exc:  # noqa: BLE001 - 单条失败不影响其它会话
                    await session.rollback()
                    logger.warning(
                        "worker.memory_batch_failed",
                        conversation_id=conversation_id,
                        error=repr(exc),
                    )

        logger.info("兜底记忆入库 %d 块 / %d 条会话", total, len(ids))
        return total


class WorkerSettings:
    """ARQ 的启动配置。

    注意：cron 任务在每个 worker 实例上都会运行。
    如果以后把 worker 扩成多实例，需要把定时任务拆到单独进程，
    否则会对账多次、清理多次（虽然幂等，但没必要）。
    """

    functions = [
        ping,
        index_diary,
        index_conversation_memories,
        delete_diary_vectors,
        delete_user_vectors,
    ]
    # 错开整点执行，避免和其他系统的定时任务撞车
    cron_jobs = [
        cron(reconcile_coins, hour=3, minute=17),
        cron(cleanup_agent_conversations, hour=4, minute=7),
        cron(expire_agent_actions, hour=4, minute=17),
        cron(cleanup_refresh_tokens, hour=4, minute=27),
        # 会话记忆：补那些「离开页面没触发成功」的
        cron(index_all_memories, hour=4, minute=37),
        # 向量对账：Chroma 少数据不会报错，只能靠主动比对修回。
        # 每小时一次，别等一天——用户半天内就会觉得「Ta 忘了我说的」
        cron(reconcile_vectors, minute=7),
    ]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
