"""数据访问层：商城的所有 SQL 都在这里。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.mall.models import MallItem, MallOrder


async def create_item(
    session: AsyncSession,
    *,
    couple_id: int,
    creator_id: int,
    title: str,
    description: str | None,
    price_coins: int,
) -> MallItem:
    item = MallItem(
        couple_id=couple_id,
        creator_id=creator_id,
        title=title,
        description=description,
        price_coins=price_coins,
    )
    session.add(item)
    await session.flush()
    return item


async def get_item(session: AsyncSession, item_id: int) -> MallItem | None:
    return await session.get(MallItem, item_id)


async def get_item_for_update(session: AsyncSession, item_id: int) -> MallItem | None:
    return await session.scalar(
        select(MallItem).where(MallItem.id == item_id).with_for_update()
    )


async def list_approved(session: AsyncSession, couple_id: int) -> list[MallItem]:
    stmt = (
        select(MallItem)
        .where(MallItem.couple_id == couple_id, MallItem.status == "approved")
        .order_by(MallItem.id.desc())
    )
    return list(await session.scalars(stmt))


async def list_by_creator(
    session: AsyncSession, couple_id: int, creator_id: int
) -> list[MallItem]:
    stmt = (
        select(MallItem)
        .where(MallItem.couple_id == couple_id, MallItem.creator_id == creator_id)
        .order_by(MallItem.id.desc())
    )
    return list(await session.scalars(stmt))


async def create_order(
    session: AsyncSession, *, item_id: int, couple_id: int, buyer_id: int, price: int
) -> MallOrder:
    order = MallOrder(
        item_id=item_id, couple_id=couple_id, buyer_id=buyer_id, price=price
    )
    session.add(order)
    await session.flush()
    return order


async def get_order_for_update(session: AsyncSession, order_id: int) -> MallOrder | None:
    return await session.scalar(
        select(MallOrder).where(MallOrder.id == order_id).with_for_update()
    )


async def list_orders(session: AsyncSession, couple_id: int) -> list[MallOrder]:
    stmt = (
        select(MallOrder)
        .where(MallOrder.couple_id == couple_id)
        .order_by(MallOrder.id.desc())
    )
    return list(await session.scalars(stmt))
