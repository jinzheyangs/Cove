"""数据访问层：情侣关系与邀请码的所有 SQL 都在这里。"""

from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.couples.models import Couple, CoupleInvite
from app.modules.users.models import User


async def get_active_by_user(session: AsyncSession, user_id: int) -> Couple | None:
    return await session.scalar(
        select(Couple).where(
            Couple.status == "active",
            or_(Couple.user1_id == user_id, Couple.user2_id == user_id),
        )
    )


async def get_active_invite_by_code(
    session: AsyncSession, code: str
) -> CoupleInvite | None:
    return await session.scalar(
        select(CoupleInvite).where(
            CoupleInvite.code == code,
            CoupleInvite.status == "active",
        )
    )


async def create_invite(
    session: AsyncSession, *, inviter_id: int, code: str, expires_at: datetime
) -> CoupleInvite:
    invite = CoupleInvite(inviter_id=inviter_id, code=code, expires_at=expires_at)
    session.add(invite)
    await session.flush()
    return invite


async def lock_users(session: AsyncSession, user_ids: list[int]) -> None:
    """按 id 升序锁定用户行，避免并发双重绑定和死锁。"""
    await session.execute(
        select(User.id).where(User.id.in_(user_ids)).order_by(User.id).with_for_update()
    )


async def create_couple(
    session: AsyncSession, *, user1_id: int, user2_id: int, bind_at: datetime
) -> Couple:
    couple = Couple(user1_id=user1_id, user2_id=user2_id, status="active", bind_at=bind_at)
    session.add(couple)
    await session.flush()
    return couple
