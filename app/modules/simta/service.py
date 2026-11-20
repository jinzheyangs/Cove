"""业务层：模拟TA（数字分身）的授权与偏好。

硬规则：使用对方数据前必须对方授权，撤销即停用。
"""

import asyncio

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.queue import enqueue
from app.modules.audit import service as audit_service
from app.modules.couples.models import Couple
from app.modules.simta import repository as repo
from app.modules.simta.schemas import PersonaStateOut
from app.modules.users.models import User

logger = structlog.get_logger("simta")

# 后台收尾任务（向量清理）的引用集合，防止被 GC
_bg_tasks: set = set()


def _partner_id(couple: Couple, user_id: int) -> int:
    """关系里的另一个人，也就是被模拟的对象。"""
    return couple.user2_id if couple.user1_id == user_id else couple.user1_id


async def set_consent(
    session: AsyncSession, couple: Couple, user: User, authorized: bool
) -> None:
    """开启或撤销授权。

    撤销会写审计日志：这是敏感操作，必须留痕。
    """
    await repo.upsert_consent(session, couple.id, user.id, authorized)
    if not authorized:
        await audit_service.record(
            session,
            user_id=user.id,
            couple_id=couple.id,
            action="simta.consent_revoke",
            target_type="persona_consent",
            target_id=user.id,
        )
    await session.commit()

    # 撤销授权后必须把已经索引的向量删掉，否则数据还留在向量库里。
    # 这件事不该堵在返回路径上：授权已经立刻失效，向量清理是收尾工作，
    # 丢给后台跑，请求马上返回（Redis 不可用时尤其重要）。
    if not authorized:
        task = asyncio.create_task(
            _cleanup_vectors_in_background(couple.id, user.id),
            name=f"simta_cleanup_{couple.id}_{user.id}",
        )
        # 持有引用：否则任务可能在跑完前被 GC 掉
        _bg_tasks.add(task)
        task.add_done_callback(_bg_tasks.discard)


async def _cleanup_vectors_in_background(couple_id: int, user_id: int) -> None:
    """后台清理向量。失败只记日志，不把异常抛给已经返回的请求。"""
    try:
        await enqueue("delete_user_vectors", couple_id, user_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "simta.vector_cleanup_failed",
            couple_id=couple_id,
            user_id=user_id,
            error=repr(exc),
        )


async def get_state(
    session: AsyncSession, couple: Couple, user: User
) -> PersonaStateOut:
    """返回当前的授权与偏好状态。"""
    my_consent = await repo.get_consent(session, couple.id, user.id)
    partner_consent = await repo.get_consent(
        session, couple.id, _partner_id(couple, user.id)
    )
    settings = await repo.get_settings(session, couple.id, user.id)

    return PersonaStateOut(
        my_consent=bool(my_consent and my_consent.authorized),
        partner_consent=bool(partner_consent and partner_consent.authorized),
        fidelity=settings.fidelity if settings else "idealized",
    )
