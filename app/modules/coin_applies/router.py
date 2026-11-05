"""金币申请的 HTTP 接口。"""

from fastapi import APIRouter

from app.core.deps import CurrentUser, SessionDep
from app.core.schemas import Envelope
from app.modules.coin_applies import service
from app.modules.coin_applies.schemas import (
    ApplyCreate,
    ApplyOut,
    ApproveRequest,
    RejectRequest,
)
from app.modules.couples.deps import CurrentCouple

router = APIRouter(prefix="/coin-applies", tags=["coin-applies"])


@router.post("", response_model=Envelope[ApplyOut])
async def create_apply(
    body: ApplyCreate, user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[ApplyOut]:
    """发起申请。对方会在 /pending 里看到。"""
    item = await service.apply(session, couple, user, body.amount, body.reason)
    return Envelope(data=ApplyOut.model_validate(item))


@router.get("", response_model=Envelope[list[ApplyOut]])
async def list_mine(user: CurrentUser, session: SessionDep) -> Envelope[list[ApplyOut]]:
    """我发起过的申请（所有状态）。"""
    items = await service.list_mine(session, user)
    return Envelope(data=[ApplyOut.model_validate(i) for i in items])


@router.get("/pending", response_model=Envelope[list[ApplyOut]])
async def list_pending(
    user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[list[ApplyOut]]:
    """对方发起的、等我审批的申请。"""
    items = await service.list_pending_for_me(session, couple, user)
    return Envelope(data=[ApplyOut.model_validate(i) for i in items])


@router.post("/{apply_id}/approve", response_model=Envelope[ApplyOut])
async def approve(
    apply_id: int,
    body: ApproveRequest,
    user: CurrentUser,
    couple: CurrentCouple,
    session: SessionDep,
) -> Envelope[ApplyOut]:
    """通过申请，可附带调整后的金额。"""
    item = await service.approve(session, couple, user, apply_id, body.amount, body.remark)
    return Envelope(data=ApplyOut.model_validate(item))


@router.post("/{apply_id}/reject", response_model=Envelope[ApplyOut])
async def reject(
    apply_id: int,
    body: RejectRequest,
    user: CurrentUser,
    couple: CurrentCouple,
    session: SessionDep,
) -> Envelope[ApplyOut]:
    """拒绝申请，可附理由。"""
    item = await service.reject(session, couple, user, apply_id, body.remark)
    return Envelope(data=ApplyOut.model_validate(item))
