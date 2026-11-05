"""数据访问层：日记相关的所有 SQL 都在这里。

约定：不 commit，事务由 service 控制。
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.diaries.models import Diary


async def create(session: AsyncSession, *, couple_id: int, author_id: int, **values) -> Diary:
    """插入日记。title/content 由 EncryptedText 自动加密。"""
    diary = Diary(couple_id=couple_id, author_id=author_id, **values)
    session.add(diary)
    await session.flush()
    return diary


async def get(session: AsyncSession, diary_id: int) -> Diary | None:
    """按主键读取。越权判断在 service 层做。"""
    return await session.get(Diary, diary_id)


async def list_diaries(
    session: AsyncSession,
    couple_id: int,
    *,
    mode: str | None = None,
    event_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Diary]:
    """按关系查询日记，支持按模式和事件关联过滤。

    event_id 过滤就是「各自视角」的读取方式：
    传同一个 event_id，拿回两个人的两篇。
    """
    stmt = select(Diary).where(Diary.couple_id == couple_id)
    if mode:
        stmt = stmt.where(Diary.mode == mode)
    if event_id:
        stmt = stmt.where(Diary.event_id == event_id)
    stmt = stmt.order_by(Diary.id.desc()).limit(limit).offset(offset)
    return list(await session.scalars(stmt))


async def delete(session: AsyncSession, diary: Diary) -> None:
    """物理删除。日记没有保留价值，删了就删了。"""
    await session.delete(diary)
    await session.flush()
