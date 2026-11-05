"""数据访问层：站内通知。

约定：写操作不 commit（notify 由业务事务提交）；
标记已读这类独立操作由 service commit。
"""

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.models import Notification


async def create(session: AsyncSession, **values: object) -> Notification:
    """插入通知并 flush，跟随调用方事务。"""
    notification = Notification(**values)
    session.add(notification)
    await session.flush()
    return notification


async def list_for_user(
    session: AsyncSession,
    user_id: int,
    *,
    unread_only: bool,
    limit: int,
    offset: int,
) -> list[Notification]:
    """列出用户的通知，时间倒序。"""
    stmt = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    stmt = stmt.order_by(Notification.id.desc()).limit(limit).offset(offset)
    return list(await session.scalars(stmt))


async def count_unread(session: AsyncSession, user_id: int) -> int:
    """统计未读数。"""
    value = await session.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
    )
    return int(value or 0)


async def mark_read(session: AsyncSession, notification_id: int, user_id: int) -> bool:
    """把一条通知标记为已读。

    条件里带 user_id：不能标记别人的通知。
    返回是否真的更新了一行。
    """
    result = await session.execute(
        update(Notification)
        .where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        .values(is_read=True)
    )
    return (result.rowcount or 0) > 0


async def mark_all_read(session: AsyncSession, user_id: int) -> int:
    """把该用户全部未读通知标记为已读，返回更新数量。"""
    result = await session.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    return result.rowcount or 0
