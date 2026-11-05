"""业务层：情侣绑定规则。"""

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.audit import service as audit_service
from app.modules.couples import repository as repo
from app.modules.couples.models import Couple, CoupleInvite
from app.modules.notifications import service as notification_service
from app.modules.users.models import User

# 去掉了容易混淆的 0/O/I/1
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_INVITE_TTL = timedelta(hours=24)


def _generate_code() -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))


async def create_invite(session: AsyncSession, user: User) -> CoupleInvite:
    if await repo.get_active_by_user(session, user.id) is not None:
        raise AppError("你已经绑定过伴侣了", code=2001, status_code=409)

    # 邀请码理论上可能碰撞，重试几次
    for _ in range(5):
        try:
            invite = await repo.create_invite(
                session,
                inviter_id=user.id,
                code=_generate_code(),
                expires_at=datetime.now(UTC) + _INVITE_TTL,
            )
            await session.commit()
        except IntegrityError:
            await session.rollback()
            continue

        await session.refresh(invite)
        return invite

    raise AppError("邀请码生成失败，请重试", code=2002, status_code=500)


async def bind(session: AsyncSession, user: User, code: str) -> Couple:
    invite = await repo.get_active_invite_by_code(session, code.strip().upper())
    if invite is None:
        raise AppError("邀请码无效", code=2003, status_code=404)
    if invite.expires_at <= datetime.now(UTC):
        raise AppError("邀请码已过期", code=2004, status_code=410)
    if invite.inviter_id == user.id:
        raise AppError("不能绑定自己", code=2005, status_code=400)

    ids = sorted({invite.inviter_id, user.id})
    await repo.lock_users(session, ids)

    if await repo.get_active_by_user(session, user.id) is not None:
        await session.rollback()
        raise AppError("你已经绑定过伴侣了", code=2001, status_code=409)
    if await repo.get_active_by_user(session, invite.inviter_id) is not None:
        await session.rollback()
        raise AppError("对方已经绑定过伴侣了", code=2006, status_code=409)

    couple = await repo.create_couple(
        session,
        user1_id=ids[0],
        user2_id=ids[1],
        bind_at=datetime.now(UTC),
    )
    invite.status = "used"
    await notification_service.notify(
        session,
        user_id=invite.inviter_id,
        type="couple.bound",
        title="你们已经绑定啦",
        related_type="couple",
        related_id=couple.id,
    )
    await audit_service.record(
        session,
        user_id=user.id,
        couple_id=couple.id,
        action="couple.bind",
        target_type="couple",
        target_id=couple.id,
    )
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError("绑定失败，请重试", code=2007, status_code=409) from exc

    await session.refresh(couple)
    return couple


async def get_active_couple(session: AsyncSession, user_id: int) -> Couple | None:
    return await repo.get_active_by_user(session, user_id)


async def unbind(
    session: AsyncSession,
    couple: Couple,
    user: User,
    confirm: bool,
    reason: str | None = None,
) -> Couple:
    """解除绑定。数据不删除，双方仍然可以导出自己的记录。"""
    if not confirm:
        raise AppError("请确认解除绑定", code=2008, status_code=400)

    couple.status = "unbound"
    couple.unbound_at = datetime.now(UTC)
    await audit_service.record(
        session,
        user_id=user.id,
        couple_id=couple.id,
        action="couple.unbind",
        target_type="couple",
        target_id=couple.id,
        detail={"reason": reason} if reason else None,
    )
    await session.commit()
    await session.refresh(couple)
    return couple
