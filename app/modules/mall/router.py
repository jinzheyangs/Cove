"""商城的 HTTP 接口。

权限约定：
- 上架：任意一方
- 审批 / 拒绝：只能是另一方
- 下架：只能是创建者
- 购买：只能是另一方
- 核销：只能是商品创建者
"""

from fastapi import APIRouter

from app.core.deps import CurrentUser, SessionDep
from app.core.schemas import Envelope
from app.modules.couples.deps import CurrentCouple
from app.modules.mall import service
from app.modules.mall.schemas import (
    ItemApprove,
    ItemCreate,
    ItemOut,
    ItemReject,
    OrderCreate,
    OrderOut,
)

router = APIRouter(prefix="/mall", tags=["mall"])


@router.post("/items", response_model=Envelope[ItemOut])
async def create_item(
    body: ItemCreate, user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[ItemOut]:
    """上架商品，等待对方审批价格。"""
    item = await service.create_item(session, couple, user, body)
    return Envelope(data=ItemOut.model_validate(item))


@router.get("/items", response_model=Envelope[list[ItemOut]])
async def list_items(
    couple: CurrentCouple, session: SessionDep
) -> Envelope[list[ItemOut]]:
    """已上架商品列表（双方都能看到同一份）。"""
    items = await service.list_items(session, couple)
    return Envelope(data=[ItemOut.model_validate(i) for i in items])


@router.get("/items/mine", response_model=Envelope[list[ItemOut]])
async def list_my_items(
    user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[list[ItemOut]]:
    """我上架的商品，包含待审批 / 被拒绝 / 已下架。"""
    items = await service.list_my_items(session, couple, user)
    return Envelope(data=[ItemOut.model_validate(i) for i in items])


@router.post("/items/{item_id}/approve", response_model=Envelope[ItemOut])
async def approve_item(
    item_id: int,
    body: ItemApprove,
    user: CurrentUser,
    couple: CurrentCouple,
    session: SessionDep,
) -> Envelope[ItemOut]:
    """审批通过，可修改最终价格。"""
    item = await service.approve_item(session, couple, user, item_id, body.price_coins)
    return Envelope(data=ItemOut.model_validate(item))


@router.post("/items/{item_id}/reject", response_model=Envelope[ItemOut])
async def reject_item(
    item_id: int,
    body: ItemReject,
    user: CurrentUser,
    couple: CurrentCouple,
    session: SessionDep,
) -> Envelope[ItemOut]:
    """拒绝上架。"""
    item = await service.reject_item(session, couple, user, item_id, body.reason)
    return Envelope(data=ItemOut.model_validate(item))


@router.post("/items/{item_id}/offline", response_model=Envelope[ItemOut])
async def offline_item(
    item_id: int, user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[ItemOut]:
    """下架自己上架的商品。"""
    item = await service.offline_item(session, couple, user, item_id)
    return Envelope(data=ItemOut.model_validate(item))


@router.post("/orders", response_model=Envelope[OrderOut])
async def buy(
    body: OrderCreate, user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[OrderOut]:
    """购买商品：扣币并生成待兑现订单。"""
    order = await service.buy(session, couple, user, body.item_id)
    return Envelope(data=OrderOut.model_validate(order))


@router.get("/orders", response_model=Envelope[list[OrderOut]])
async def list_orders(
    couple: CurrentCouple, session: SessionDep
) -> Envelope[list[OrderOut]]:
    """关系内的全部订单。"""
    orders = await service.list_orders(session, couple)
    return Envelope(data=[OrderOut.model_validate(o) for o in orders])


@router.post("/orders/{order_id}/complete", response_model=Envelope[OrderOut])
async def complete_order(
    order_id: int, user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[OrderOut]:
    """服务提供方确认订单已完成。"""
    order = await service.complete_order(session, couple, user, order_id)
    return Envelope(data=OrderOut.model_validate(order))
