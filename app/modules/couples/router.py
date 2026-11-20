"""情侣绑定的 HTTP 接口。"""

from fastapi import APIRouter

from app.core.deps import CurrentUser, SessionDep
from app.core.schemas import Envelope
from app.core.storage import get_storage
from app.modules.couples import service
from app.modules.couples.deps import CurrentCouple
from app.modules.couples.schemas import (
    BindRequest,
    CoupleOut,
    CoupleUpdate,
    InviteOut,
    PartnerOut,
    UnbindRequest,
    UsStatsOut,
)
from app.modules.users.models import User

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


@router.get("/us/stats", response_model=Envelope[UsStatsOut])
async def us_stats(
    user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[UsStatsOut]:
    """解绑前先让两个人看清楚：这段关系里攒下了多少东西。

    只统计、不改状态；解绑本身仍然要 /couples/unbind + confirm。
    """
    return Envelope(data=await service.us_stats(session, couple, user))


@router.get("/me", response_model=Envelope[CoupleOut | None])
async def get_my_couple(
    user: CurrentUser, session: SessionDep
) -> Envelope[CoupleOut | None]:
    """查询当前关系。没绑定时 data 为 null，不是报错。

    顺带把另一半的昵称带上：日记这类「两边各写一段」的界面要显示名字，
    否则前端只能写死一个假名字。
    """
    couple = await service.get_active_couple(session, user.id)
    if couple is None:
        return Envelope(data=None)

    out = CoupleOut.model_validate(couple)
    partner_id = couple.user2_id if couple.user1_id == user.id else couple.user1_id
    partner = await session.get(User, partner_id)
    if partner is not None:
        storage = get_storage()
        out.partner = PartnerOut(
            id=partner.id,
            nickname=partner.nickname,
            avatar_url=storage.build_url(partner.avatar) if partner.avatar else None,
        )
    return Envelope(data=out)


@router.put("/me", response_model=Envelope[CoupleOut])
async def update_my_couple(
    body: CoupleUpdate,
    couple: CurrentCouple,
    session: SessionDep,
) -> Envelope[CoupleOut]:
    """更新关系资料。目前只有「在一起」的起始日。

    未绑定会由 CurrentCouple 直接挡成 409。
    """
    updated = await service.update_start_date(session, couple, body.start_date)
    return Envelope(data=CoupleOut.model_validate(updated))
