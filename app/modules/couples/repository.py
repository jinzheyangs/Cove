"""数据访问层：情侣关系与邀请码的所有 SQL 都在这里。

约定：不 commit，事务由 service 控制。
"""

from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.couples.models import Couple, CoupleInvite
from app.modules.users.models import User


async def get_active_by_user(session: AsyncSession, user_id: int) -> Couple | None:
    """取该用户当前生效的关系。

    一个人最多只有一段 active 关系，所以用 scalar 而不是 scalars。
    or_ 两个字段是因为用户可能落在 user1 也可能落在 user2。
    """
    return await session.scalar(
        select(Couple).where(
            Couple.status == "active",
            or_(Couple.user1_id == user_id, Couple.user2_id == user_id),
        )
    )


async def get_active_invite_by_code(
    session: AsyncSession, code: str
) -> CoupleInvite | None:
    """按码查有效邀请。已使用（used）的码查不到。"""
    return await session.scalar(
        select(CoupleInvite).where(
            CoupleInvite.code == code,
            CoupleInvite.status == "active",
        )
    )


async def create_invite(
    session: AsyncSession, *, inviter_id: int, code: str, expires_at: datetime
) -> CoupleInvite:
    """插入邀请码并 flush。

    唯一索引冲突会抛 IntegrityError，由 service 捕获后换一个码重试。
    """
    invite = CoupleInvite(inviter_id=inviter_id, code=code, expires_at=expires_at)
    session.add(invite)
    await session.flush()
    return invite


async def lock_users(session: AsyncSession, user_ids: list[int]) -> None:
    """按 id 升序锁定用户行，避免并发双重绑定和死锁。

    为什么升序：两个并发请求如果各自按不同顺序锁同一个用户，
    会互相等待形成死锁。统一排序后永远不会出现环。

    锁在事务结束时释放，所以调用方要尽快 commit 或 rollback。
    """
    await session.execute(
        select(User.id).where(User.id.in_(user_ids)).order_by(User.id).with_for_update()
    )


async def create_couple(
    session: AsyncSession, *, user1_id: int, user2_id: int, bind_at: datetime
) -> Couple:
    """创建关系。调用方必须保证 user1_id < user2_id。"""
    couple = Couple(user1_id=user1_id, user2_id=user2_id, status="active", bind_at=bind_at)
    session.add(couple)
    await session.flush()
    return couple
