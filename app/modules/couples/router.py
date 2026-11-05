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
    invite = await service.create_invite(session, user)
    return Envelope(data=InviteOut(code=invite.code, expires_at=invite.expires_at))


@router.post("/bind", response_model=Envelope[CoupleOut])
async def bind(
    body: BindRequest, user: CurrentUser, session: SessionDep
) -> Envelope[CoupleOut]:
    couple = await service.bind(session, user, body.code)
    return Envelope(data=CoupleOut.model_validate(couple))


@router.post("/unbind", response_model=Envelope[CoupleOut])
async def unbind(
    body: UnbindRequest,
    user: CurrentUser,
    couple: CurrentCouple,
    session: SessionDep,
) -> Envelope[CoupleOut]:
    updated = await service.unbind(session, couple, user, body.confirm, body.reason)
    return Envelope(data=CoupleOut.model_validate(updated))


@router.get("/me", response_model=Envelope[CoupleOut | None])
async def get_my_couple(
    user: CurrentUser, session: SessionDep
) -> Envelope[CoupleOut | None]:
    couple = await service.get_active_couple(session, user.id)
    return Envelope(data=CoupleOut.model_validate(couple) if couple else None)
