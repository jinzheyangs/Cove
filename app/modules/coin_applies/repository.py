"""数据访问层：金币申请的所有 SQL 都在这里。"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.coin_applies.models import CoinApply


async def create(
    session: AsyncSession, *, couple_id: int, applicant_id: int, amount: int, reason: str
) -> CoinApply:
    apply_item = CoinApply(
        couple_id=couple_id, applicant_id=applicant_id, amount=amount, reason=reason
    )
    session.add(apply_item)
    await session.flush()
    return apply_item


async def get_for_update(session: AsyncSession, apply_id: int) -> CoinApply | None:
    return await session.scalar(
        select(CoinApply).where(CoinApply.id == apply_id).with_for_update()
    )


async def list_by_applicant(session: AsyncSession, applicant_id: int) -> list[CoinApply]:
    stmt = (
        select(CoinApply)
        .where(CoinApply.applicant_id == applicant_id)
        .order_by(CoinApply.id.desc())
    )
    return list(await session.scalars(stmt))


async def list_pending_by_applicant(
    session: AsyncSession, couple_id: int, applicant_id: int
) -> list[CoinApply]:
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
    value = await session.scalar(
        select(func.count())
        .select_from(CoinApply)
        .where(CoinApply.applicant_id == applicant_id, CoinApply.status == "pending")
    )
    return int(value or 0)
