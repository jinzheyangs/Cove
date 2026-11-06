"""数据访问层：商城的所有 SQL 都在这里。

约定：不 commit，事务由 service 控制。
"""

from sqlalchemy import func, select
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
    max_orders: int | None = None,
) -> MallItem:
    """插入商品，初始状态是 pending。"""
    item = MallItem(
        couple_id=couple_id,
        creator_id=creator_id,
        title=title,
        description=description,
        price_coins=price_coins,
        max_orders=max_orders,
    )
    session.add(item)
    await session.flush()
    return item


async def get_item(session: AsyncSession, item_id: int) -> MallItem | None:
    """普通读取，不加锁。用于核销时检查创建者。"""
    return await session.get(MallItem, item_id)


async def get_item_for_update(session: AsyncSession, item_id: int) -> MallItem | None:
    """加行锁读取商品。

    审批、下架、购买都要锁：
    否则“下架”和“购买”并发时，可能刚好在间隙里成交。
    """
    return await session.scalar(
        select(MallItem).where(MallItem.id == item_id).with_for_update()
    )


async def list_approved(session: AsyncSession, couple_id: int) -> list[MallItem]:
    """商城首页：只看已上架的商品。"""
    stmt = (
        select(MallItem)
        .where(MallItem.couple_id == couple_id, MallItem.status == "approved")
        .order_by(MallItem.id.desc())
    )
    return list(await session.scalars(stmt))


async def list_by_creator(
    session: AsyncSession, couple_id: int, creator_id: int
) -> list[MallItem]:
    """我上架过的全部商品，包含待审批和被拒绝的。"""
    stmt = (
        select(MallItem)
        .where(MallItem.couple_id == couple_id, MallItem.creator_id == creator_id)
        .order_by(MallItem.id.desc())
    )
    return list(await session.scalars(stmt))


async def create_order(
    session: AsyncSession,
    *,
    item_id: int,
    couple_id: int,
    buyer_id: int,
    price: int,
    idempotency_key: str | None = None,
) -> MallOrder:
    """创建待兑现订单。price 是成交时的价格快照。"""
    order = MallOrder(
        item_id=item_id,
        couple_id=couple_id,
        buyer_id=buyer_id,
        price=price,
        idempotency_key=idempotency_key,
    )
    session.add(order)
    await session.flush()
    return order


async def get_order_by_idempotency_key(
    session: AsyncSession, couple_id: int, key: str
) -> MallOrder | None:
    """按幂等键查已创建的订单。"""
    return await session.scalar(
        select(MallOrder).where(
            MallOrder.couple_id == couple_id,
            MallOrder.idempotency_key == key,
        )
    )


async def count_orders(session: AsyncSession, item_id: int) -> int:
    """统计已占用库存的订单数。

    只算 pending 和 completed：
    已取消的订单不应该继续占库存。
    """
    value = await session.scalar(
        select(func.count())
        .select_from(MallOrder)
        .where(
            MallOrder.item_id == item_id,
            MallOrder.status.in_(["pending", "completed"]),
        )
    )
    return int(value or 0)


async def get_order_for_update(session: AsyncSession, order_id: int) -> MallOrder | None:
    """加行锁读取订单，防止重复核销。"""
    return await session.scalar(
        select(MallOrder).where(MallOrder.id == order_id).with_for_update()
    )


async def list_orders(session: AsyncSession, couple_id: int) -> list[MallOrder]:
    """关系内的全部订单，按时间倒序。"""
    stmt = (
        select(MallOrder)
        .where(MallOrder.couple_id == couple_id)
        .order_by(MallOrder.id.desc())
    )
    return list(await session.scalars(stmt))
