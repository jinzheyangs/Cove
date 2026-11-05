"""情侣绑定的 HTTP 接口。"""

from fastapi import APIRouter

from app.core.deps import CurrentUser, SessionDep
from app.core.schemas import Envelope
from app.modules.couples import service
from app.modules.couples.deps import CurrentCouple
from app.modules.couples.schemas import (
    BindRequest,
    CoupleOut,
    InviteOut,
    UnbindRequest,
)

router = APIRouter(prefix="/couples", tags=["couples"])


@router.post("/invite", response_model=Envelope[InviteOut])
async def create_invite(user: CurrentUser, session: SessionDep) -> Envelope[InviteOut]:
    """生成邀请码，交给对方输入。24 小时内有效。"""
    invite = await service.create_invite(session, user)
    return Envelope(data=InviteOut(code=invite.code, expires_at=invite.expires_at))


@router.post("/bind", response_model=Envelope[CoupleOut])
async def bind(
    body: BindRequest, user: CurrentUser, session: SessionDep
) -> Envelope[CoupleOut]:
    """用对方的邀请码完成绑定。"""
    couple = await service.bind(session, user, body.code)
    return Envelope(data=CoupleOut.model_validate(couple))


@router.post("/unbind", response_model=Envelope[CoupleOut])
async def unbind(
    body: UnbindRequest,
    user: CurrentUser,
    couple: CurrentCouple,
    session: SessionDep,
) -> Envelope[CoupleOut]:
    """解除绑定。必须显式传 confirm=true。

    CurrentCouple 依赖保证当前确实有一段生效的关系。
    """
    updated = await service.unbind(session, couple, user, body.confirm, body.reason)
    return Envelope(data=CoupleOut.model_validate(updated))


@router.get("/me", response_model=Envelope[CoupleOut | None])
async def get_my_couple(
    user: CurrentUser, session: SessionDep
) -> Envelope[CoupleOut | None]:
    """查询当前关系。没绑定时 data 为 null，不是报错。"""
    couple = await service.get_active_couple(session, user.id)
    return Envelope(data=CoupleOut.model_validate(couple) if couple else None)
