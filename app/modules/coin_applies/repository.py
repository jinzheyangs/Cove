"""数据访问层：金币申请的所有 SQL 都在这里。

约定：不 commit，事务由 service 控制。
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.coin_applies.models import CoinApply


async def create(
    session: AsyncSession, *, couple_id: int, applicant_id: int, amount: int, reason: str
) -> CoinApply:
    """插入一条待审批申请。"""
    apply_item = CoinApply(
        couple_id=couple_id, applicant_id=applicant_id, amount=amount, reason=reason
    )
    session.add(apply_item)
    await session.flush()
    return apply_item


async def get_for_update(session: AsyncSession, apply_id: int) -> CoinApply | None:
    """加行锁读取申请。

    审批时必须先锁：
    两个人同时点“通过”，不加锁会各发一次金币。
    """
    return await session.scalar(
        select(CoinApply).where(CoinApply.id == apply_id).with_for_update()
    )


async def list_by_applicant(session: AsyncSession, applicant_id: int) -> list[CoinApply]:
    """我发起过的全部申请，按时间倒序。"""
    stmt = (
        select(CoinApply)
        .where(CoinApply.applicant_id == applicant_id)
        .order_by(CoinApply.id.desc())
    )
    return list(await session.scalars(stmt))


async def list_pending_by_applicant(
    session: AsyncSession, couple_id: int, applicant_id: int
) -> list[CoinApply]:
    """指定用户在某个关系内、还没处理的申请。

    用于「对方发起的、等我审批的」列表。
    """
    stmt = (
        select(CoinApply)
        .where(
            CoinApply.couple_id == couple_id,
            CoinApply.applicant_id == applicant_id,
            CoinApply.status == "pending",
        )
        .order_by(CoinApply.id.desc())
    )
    return list(await session.scalars(stmt))


async def count_pending(session: AsyncSession, applicant_id: int) -> int:
    """统计待审批数量，用于限制骚扰式刷申请。"""
    value = await session.scalar(
        select(func.count())
        .select_from(CoinApply)
        .where(CoinApply.applicant_id == applicant_id, CoinApply.status == "pending")
    )
    return int(value or 0)
