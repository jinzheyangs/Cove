"""数据访问层：账本相关的所有 SQL 都在这里。"""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bills.models import Bill


async def create(session: AsyncSession, *, couple_id: int, payer_id: int, **values) -> Bill:
    bill = Bill(couple_id=couple_id, payer_id=payer_id, **values)
    session.add(bill)
    await session.flush()
    return bill


async def get(session: AsyncSession, bill_id: int) -> Bill | None:
    return await session.get(Bill, bill_id)


def _visible_to(viewer_id: int):
    """隐私支出只对记账人自己可见。"""
    return or_(Bill.is_private.is_(False), Bill.payer_id == viewer_id)


async def list_visible(
    session: AsyncSession,
    couple_id: int,
    viewer_id: int,
    *,
    bill_type: str | None = None,
    scope: str | None = None,
) -> list[Bill]:
    stmt = select(Bill).where(Bill.couple_id == couple_id, _visible_to(viewer_id))
    if bill_type:
        stmt = stmt.where(Bill.type == bill_type)
    if scope:
        stmt = stmt.where(Bill.scope == scope)
    stmt = stmt.order_by(Bill.id.desc())
    return list(await session.scalars(stmt))


async def delete(session: AsyncSession, bill: Bill) -> None:
    await session.delete(bill)
    await session.flush()
