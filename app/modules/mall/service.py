"""业务层：商城的上下架、购买与核销。

两个关键约束：
1. 不能购买自己上架的商品——否则金币经济失去意义
2. 购买时扣币、建订单、发通知在同一个事务里，不会出现扣了钱没订单
"""

from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
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
    """上架商品，提交后直接处于 approved 状态，无需对方审批。

    价格以创建者填写的 price_coins 为准。
    """
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
    """商城列表：只返回已上架的商品。"""
    return await repo.list_approved(session, couple.id)


async def list_my_items(
    session: AsyncSession, couple: Couple, user: User
) -> list[MallItem]:
    """我上架的商品，包含已上架和已下架的，方便查看状态。"""
    return await repo.list_by_creator(session, couple.id, user.id)


async def offline_item(
    session: AsyncSession, couple: Couple, user: User, item_id: int
) -> MallItem:
    """下架。只有创建者可以下架，且只能从 approved 状态转。

    加锁是为了和购买互斥：避免在“检查状态”和“改成 offline”之间被买走。
    """
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


async def edit_item(
    session: AsyncSession,
    couple: Couple,
    user: User,
    item_id: int,
    body: ItemCreate,
) -> MallItem:
    """创建者编辑商品，保存后直接生效，保持 approved。

    进行中的订单带有成交价快照，不会被这里的改动影响。
    """
    item = await repo.get_item_for_update(session, item_id)
    if item is None or item.couple_id != couple.id:
        raise AppError("商品不存在", code=7001, status_code=404)
    if item.creator_id != user.id:
        raise AppError("只能修改自己上架的商品", code=7004, status_code=403)

    item.title = body.title
    item.description = body.description
    item.price_coins = body.price_coins
    item.max_orders = body.max_orders
    await session.commit()
    await session.refresh(item)
    return item


async def buy(
    session: AsyncSession,
    couple: Couple,
    buyer: User,
    item_id: int,
    idempotency_key: str | None = None,
) -> MallOrder:
    """用金币兑换商品。

    顺序很重要：
    1. 锁商品行（和下架互斥）
    2. 校验状态、不能买自己的、库存
    3. 扣币（spend_locked，不提交）
    4. 建订单、发通知
    5. 统一提交

    任何一步失败都整体回滚，不会出现“扣了钱没订单”。
    """
    if idempotency_key:
        existing = await repo.get_order_by_idempotency_key(
            session, couple.id, idempotency_key
        )
        if existing is not None:
            return existing

    item = await repo.get_item_for_update(session, item_id)
    if item is None or item.couple_id != couple.id:
        raise AppError("商品不存在", code=7001, status_code=404)
    if item.status != "approved":
        raise AppError("这个商品还没上架", code=7006, status_code=409)
    if item.creator_id == buyer.id:
        raise AppError("不能购买自己上架的商品", code=7007, status_code=400)

    # 库存检查在商品行锁内，并发购买会串行化
    if item.max_orders is not None:
        ordered = await repo.count_orders(session, item.id)
        if ordered >= item.max_orders:
            raise AppError("这件商品已经兑换完了", code=7011, status_code=409)

    # 价格直接用商品价，并在这里快照进订单
    price = item.price_coins
    buyer_id = buyer.id

    try:
        await coin_service.spend_locked(
            session,
            couple_id=couple.id,    #这笔消费属于哪一对情侣，用来隔离数据、查账单
            spender_id=buyer_id,    #花钱的人：买家id（谁扣余额）
            amount=price,           #扣多少金币：就是前面算出来的快照价格
            ref_type="mall_item",   #这笔钱是因为什么业务扣的：mall_item = 商城兑换商品
            ref_id=item.id,         #关联业务单据id：是哪个商品
        )
        order = await repo.create_order(
            session,
            item_id=item.id,
            couple_id=couple.id,
            buyer_id=buyer_id,
            price=price,
            idempotency_key=idempotency_key,
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
    except IntegrityError:
        # 并发提交同一个幂等键：回滚会同时撤销本次扣币，返回先成功的订单。
        # key 为空时不能去查 NULL，否则可能返回一笔无关的旧订单。
        await session.rollback()
        if idempotency_key:
            existing = await repo.get_order_by_idempotency_key(
                session, couple.id, idempotency_key
            )
            if existing is not None:
                return existing
        raise
    except AppError:
        # 余额不足等业务错误：回滚扣币，商品保持原状
        await session.rollback()
        raise

    await session.refresh(order)
    return order


async def complete_order(
    session: AsyncSession, couple: Couple, user: User, order_id: int
) -> MallOrder:
    """确认订单已兑现。

    只有服务提供方（商品创建者）能确认：
    买家说自己“已经享受到了”不算数，由提供服务的人来关闭订单。
    """
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


async def cancel_order(
    session: AsyncSession, couple: Couple, user: User, order_id: int
) -> MallOrder:
    """买家取消待兑现订单，金币原路退回。

    权限和状态：
    - 只有买家本人能取消，服务方没有这个入口（403）
    - 只能取消 pending 订单；已完成 / 已取消的再点会 409，天然防重复

    退款用 mint_locked 把下单时销毁的金币等额重新发行给买家，
    和订单状态变更放在同一个事务里，不会出现“订单取消了但币没回来”。
    """
    order = await repo.get_order_for_update(session, order_id)
    if order is None or order.couple_id != couple.id:
        raise AppError("订单不存在", code=7008, status_code=404)
    if order.status != "pending":
        raise AppError("这个订单已经处理过了", code=7009, status_code=409)
    if order.buyer_id != user.id:
        raise AppError("只有买家本人可以取消订单", code=7012, status_code=403)

    item = await repo.get_item(session, order.item_id)
    try:
        await coin_service.mint_locked(
            session,
            couple_id=couple.id,
            actor_id=user.id,
            recipient_id=order.buyer_id,
            amount=order.price,
            tx_type="reward",
            ref_type="mall_order",
            ref_id=order.id,
            remark="订单取消退款",
        )
        order.status = "cancelled"
        if item is not None:
            await notification_service.notify(
                session,
                user_id=item.creator_id,
                type="mall.order_cancelled",
                title="对方取消了一笔兑换",
                content=item.title,
                related_type="mall_order",
                related_id=order.id,
            )
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    except AppError:
        await session.rollback()
        raise

    await session.refresh(order)
    return order


async def list_orders(session: AsyncSession, couple: Couple) -> list[MallOrder]:
    """关系内的全部订单。双方看到的是同一份列表。"""
    return await repo.list_orders(session, couple.id)