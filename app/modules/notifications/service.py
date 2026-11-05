"""业务层：站内通知。

notify() 只把记录加进当前事务，由调用方 commit，
保证"业务成功但通知丢了"或"通知发了但业务回滚"都不会发生。
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications import repository as repo
from app.modules.notifications.models import Notification


async def notify(
    session: AsyncSession,
    *,
    user_id: int,
    type: str,
    title: str,
    content: str | None = None,
    related_type: str | None = None,
    related_id: int | None = None,
) -> Notification:
    """写一条通知（不提交）。

    调用方通常已经在做某个业务操作，
    这个通知会和业务写入一起提交。

    注意 content 不要放秘密/日记原文，
    它不是展示正文的地方，只是简短说明。
    """
    return await repo.create(
        session,
        user_id=user_id,
        type=type,
        title=title,
        content=content,
        related_type=related_type,
        related_id=related_id,
    )


async def list_mine(
    session: AsyncSession,
    user_id: int,
    *,
    unread_only: bool,
    limit: int,
    offset: int,
) -> list[Notification]:
    """列出自己的通知。"""
    return await repo.list_for_user(
        session, user_id, unread_only=unread_only, limit=limit, offset=offset
    )


async def unread_count(session: AsyncSession, user_id: int) -> int:
    """未读数。"""
    return await repo.count_unread(session, user_id)


async def mark_read(session: AsyncSession, user_id: int, notification_id: int) -> bool:
    """标记单条已读。返回是否更新成功。"""
    updated = await repo.mark_read(session, notification_id, user_id)
    await session.commit()
    return updated


async def mark_all_read(session: AsyncSession, user_id: int) -> int:
    """全部标记已读，返回更新数量。"""
    count = await repo.mark_all_read(session, user_id)
    await session.commit()
    return count
