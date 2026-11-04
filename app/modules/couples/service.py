import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.couples.models import Couple, CoupleInvite
from app.modules.users.models import User

# 去掉了容易混淆的 0/O/I/1
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_INVITE_TTL = timedelta(hours=24)


def _generate_code() -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))


async def _active_couple(session: AsyncSession, user_id: int) -> Couple | None:
    return await session.scalar(
        select(Couple).where(
            Couple.status == "active",
            or_(Couple.user1_id == user_id, Couple.user2_id == user_id),
        )
    )


async def create_invite(session: AsyncSession, user: User) -> CoupleInvite:
    if await _active_couple(session, user.id) is not None:
        raise AppError("你已经绑定过伴侣了", code=2001, status_code=409)

    # 邀请码理论上可能碰撞，重试几次
    for _ in range(5):
        invite = CoupleInvite(
            inviter_id=user.id,
            code=_generate_code(),
            expires_at=datetime.now(timezone.utc) + _INVITE_TTL,
        )
        session.add(invite)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            continue
        await session.refresh(invite)
        return invite

    raise AppError("邀请码生成失败，请重试", code=2002, status_code=500)


async def bind(session: AsyncSession, user: User, code: str) -> Couple:
    invite = await session.scalar(
        select(CoupleInvite).where(
            CoupleInvite.code == code.strip().upper(),
            CoupleInvite.status == "active",
        )
    )
    if invite is None:
        raise AppError("邀请码无效", code=2003, status_code=404)
    if invite.expires_at <= datetime.now(timezone.utc):
        raise AppError("邀请码已过期", code=2004, status_code=410)
    if invite.inviter_id == user.id:
        raise AppError("不能绑定自己", code=2005, status_code=400)

    # 锁住双方用户行（按 id 升序），避免并发绑定同一个人
    ids = sorted({invite.inviter_id, user.id})
    await session.execute(
        select(User.id).where(User.id.in_(ids)).order_by(User.id).with_for_update()
    )

    if await _active_couple(session, user.id) is not None:
        raise AppError("你已经绑定过伴侣了", code=2001, status_code=409)
    if await _active_couple(session, invite.inviter_id) is not None:
        raise AppError("对方已经绑定过伴侣了", code=2006, status_code=409)

    couple = Couple(
        user1_id=ids[0],
        user2_id=ids[1],
        status="active",
        bind_at=datetime.now(timezone.utc),
    )
    invite.status = "used"
    session.add(couple)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError("绑定失败，请重试", code=2007, status_code=409) from exc

    await session.refresh(couple)
    return couple


async def get_active_couple(session: AsyncSession, user_id: int) -> Couple | None:
    return await _active_couple(session, user_id)
