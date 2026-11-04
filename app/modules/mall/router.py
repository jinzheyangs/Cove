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
    item = await service.create_item(session, couple, user, body)
    return Envelope(data=ItemOut.model_validate(item))


@router.get("/items", response_model=Envelope[list[ItemOut]])
async def list_items(
    couple: CurrentCouple, session: SessionDep
) -> Envelope[list[ItemOut]]:
    items = await service.list_items(session, couple)
    return Envelope(data=[ItemOut.model_validate(i) for i in items])


@router.get("/items/mine", response_model=Envelope[list[ItemOut]])
async def list_my_items(
    user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[list[ItemOut]]:
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
    item = await service.reject_item(session, couple, user, item_id, body.reason)
    return Envelope(data=ItemOut.model_validate(item))


@router.post("/items/{item_id}/offline", response_model=Envelope[ItemOut])
async def offline_item(
    item_id: int, user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[ItemOut]:
    item = await service.offline_item(session, couple, user, item_id)
    return Envelope(data=ItemOut.model_validate(item))


@router.post("/orders", response_model=Envelope[OrderOut])
async def buy(
    body: OrderCreate, user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[OrderOut]:
    order = await service.buy(session, couple, user, body.item_id)
    return Envelope(data=OrderOut.model_validate(order))


@router.get("/orders", response_model=Envelope[list[OrderOut]])
async def list_orders(
    couple: CurrentCouple, session: SessionDep
) -> Envelope[list[OrderOut]]:
    orders = await service.list_orders(session, couple)
    return Envelope(data=[OrderOut.model_validate(o) for o in orders])


@router.post("/orders/{order_id}/complete", response_model=Envelope[OrderOut])
async def complete_order(
    order_id: int, user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[OrderOut]:
    order = await service.complete_order(session, couple, user, order_id)
    return Envelope(data=OrderOut.model_validate(order))
