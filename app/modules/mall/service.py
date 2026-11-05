"""业务层：商城的上下架、购买与核销。"""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.coins import service as coin_service
from app.modules.couples.models import Couple
from app.modules.mall import repository as repo
from app.modules.mall.models import MallItem, MallOrder
from app.modules.mall.schemas import ItemCreate
from app.modules.notifications import service as notification_service
from app.modules.users.models import User


async def create_item(
    session: AsyncSession, couple: Couple, creator: User, body: ItemCreate
) -> MallItem:
    item = await repo.create_item(
        session,
        couple_id=couple.id,
        creator_id=creator.id,
        title=body.title,
        description=body.description,
        price_coins=body.price_coins,
        max_orders=body.max_orders,
    )
    await session.commit()
    await session.refresh(item)
    return item


async def list_items(session: AsyncSession, couple: Couple) -> list[MallItem]:
    return await repo.list_approved(session, couple.id)


async def list_my_items(
    session: AsyncSession, couple: Couple, user: User
) -> list[MallItem]:
    return await repo.list_by_creator(session, couple.id, user.id)


async def _get_pending_item_for_review(
    session: AsyncSession, couple: Couple, reviewer: User, item_id: int
) -> MallItem:
    item = await repo.get_item_for_update(session, item_id)
    if item is None or item.couple_id != couple.id:
        raise AppError("商品不存在", code=7001, status_code=404)
    if item.creator_id == reviewer.id:
        raise AppError("不能审批自己上架的商品", code=7002, status_code=403)
    if item.status != "pending":
        raise AppError("这个商品已经处理过了", code=7003, status_code=409)
    return item


async def approve_item(
    session: AsyncSession,
    couple: Couple,
    reviewer: User,
    item_id: int,
    price_coins: int | None = None,
) -> MallItem:
    item = await _get_pending_item_for_review(session, couple, reviewer, item_id)
    item.status = "approved"
    item.approver_id = reviewer.id
    item.approved_price = price_coins or item.price_coins
    await session.commit()
    await session.refresh(item)
    return item


async def reject_item(
    session: AsyncSession,
    couple: Couple,
    reviewer: User,
    item_id: int,
    reason: str | None = None,
) -> MallItem:
    item = await _get_pending_item_for_review(session, couple, reviewer, item_id)
    item.status = "rejected"
    item.approver_id = reviewer.id
    item.reject_reason = reason
    await session.commit()
    await session.refresh(item)
    return item


async def offline_item(
    session: AsyncSession, couple: Couple, user: User, item_id: int
) -> MallItem:
    item = await repo.get_item_for_update(session, item_id)
    if item is None or item.couple_id != couple.id:
        raise AppError("商品不存在", code=7001, status_code=404)
    if item.creator_id != user.id:
        raise AppError("只能下架自己上架的商品", code=7004, status_code=403)
    if item.status != "approved":
        raise AppError("只有已上架的商品可以下架", code=7005, status_code=409)
    item.status = "offline"
    await session.commit()
    await session.refresh(item)
    return item


async def buy(
    session: AsyncSession, couple: Couple, buyer: User, item_id: int
) -> MallOrder:
    item = await repo.get_item_for_update(session, item_id)
    if item is None or item.couple_id != couple.id:
        raise AppError("商品不存在", code=7001, status_code=404)
    if item.status != "approved":
        raise AppError("这个商品还没上架", code=7006, status_code=409)
    if item.creator_id == buyer.id:
        raise AppError("不能购买自己上架的商品", code=7007, status_code=400)

    if item.max_orders is not None:
        ordered = await repo.count_orders(session, item.id)
        if ordered >= item.max_orders:
            raise AppError("这件商品已经兑换完了", code=7011, status_code=409)

    price = item.approved_price or item.price_coins
    buyer_id = buyer.id

    try:
        await coin_service.spend_locked(
            session,
            couple_id=couple.id,
            spender_id=buyer_id,
            amount=price,
            ref_type="mall_item",
            ref_id=item.id,
        )
        order = await repo.create_order(
            session,
            item_id=item.id,
            couple_id=couple.id,
            buyer_id=buyer_id,
            price=price,
        )
        await notification_service.notify(
            session,
            user_id=item.creator_id,
            type="mall.order_created",
            title="有人兑换了你的商品",
            content=item.title,
            related_type="mall_order",
            related_id=order.id,
        )
        await session.commit()
    except AppError:
        await session.rollback()
        raise

    await session.refresh(order)
    return order


async def complete_order(
    session: AsyncSession, couple: Couple, user: User, order_id: int
) -> MallOrder:
    order = await repo.get_order_for_update(session, order_id)
    if order is None or order.couple_id != couple.id:
        raise AppError("订单不存在", code=7008, status_code=404)
    if order.status != "pending":
        raise AppError("这个订单已经处理过了", code=7009, status_code=409)

    item = await repo.get_item(session, order.item_id)
    if item is None or item.creator_id != user.id:
        raise AppError("只有提供服务的一方可以确认完成", code=7010, status_code=403)

    order.status = "completed"
    order.completed_at = datetime.now(UTC)
    await notification_service.notify(
        session,
        user_id=order.buyer_id,
        type="mall.order_completed",
        title="你的兑换已完成",
        related_type="mall_order",
        related_id=order.id,
    )
    await session.commit()
    await session.refresh(order)
    return order


async def list_orders(session: AsyncSession, couple: Couple) -> list[MallOrder]:
    return await repo.list_orders(session, couple.id)
