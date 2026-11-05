"""数据访问层：站内通知。"""

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.models import Notification


async def create(session: AsyncSession, **values: object) -> Notification:
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
    stmt = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    stmt = stmt.order_by(Notification.id.desc()).limit(limit).offset(offset)
    return list(await session.scalars(stmt))


async def count_unread(session: AsyncSession, user_id: int) -> int:
    value = await session.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
    )
    return int(value or 0)


async def mark_read(session: AsyncSession, notification_id: int, user_id: int) -> bool:
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
    result = await session.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    return result.rowcount or 0
