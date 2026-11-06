"""数据访问层：账本相关的所有 SQL 都在这里。

约定：不 commit，事务由 service 控制。
"""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bills.models import Bill


async def create(session: AsyncSession, *, couple_id: int, payer_id: int, **values) -> Bill:
    """插入账目。remark 由 EncryptedText 自动加密。"""
    bill = Bill(couple_id=couple_id, payer_id=payer_id, **values)
    session.add(bill)
    await session.flush()
    return bill


async def get_by_idempotency_key(
    session: AsyncSession, couple_id: int, key: str
) -> Bill | None:
    """按幂等键查已创建的账目。"""
    return await session.scalar(
        select(Bill).where(
            Bill.couple_id == couple_id,
            Bill.idempotency_key == key,
        )
    )


async def get(session: AsyncSession, bill_id: int) -> Bill | None:
    """按主键读取。隐私和越权判断在 service 层。"""
    return await session.get(Bill, bill_id)


def _visible_to(viewer_id: int):
    """隐私过滤条件。

    非隐私记录所有人都能看；
    隐私记录只有记账人自己能看。
    """
    return or_(Bill.is_private.is_(False), Bill.payer_id == viewer_id)


async def list_visible(
    session: AsyncSession,
    couple_id: int,
    viewer_id: int,
    *,
    bill_type: str | None = None,
    scope: str | None = None,
) -> list[Bill]:
    """列出当前用户可见的账目。

    **所有**读取路径都必须带 _visible_to，
    否则统计和列表会泄露对方的隐私支出。
    """
    stmt = select(Bill).where(Bill.couple_id == couple_id, _visible_to(viewer_id))
    if bill_type:
        stmt = stmt.where(Bill.type == bill_type)
    if scope:
        stmt = stmt.where(Bill.scope == scope)
    stmt = stmt.order_by(Bill.id.desc())
    return list(await session.scalars(stmt))


async def delete(session: AsyncSession, bill: Bill) -> None:
    """物理删除。"""
    await session.delete(bill)
    await session.flush()
