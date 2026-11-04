"""数据访问层：日记相关的所有 SQL 都在这里。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.diaries.models import Diary


async def create(session: AsyncSession, *, couple_id: int, author_id: int, **values) -> Diary:
    diary = Diary(couple_id=couple_id, author_id=author_id, **values)
    session.add(diary)
    await session.flush()
    return diary


async def get(session: AsyncSession, diary_id: int) -> Diary | None:
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
    stmt = select(Diary).where(Diary.couple_id == couple_id)
    if mode:
        stmt = stmt.where(Diary.mode == mode)
    if event_id:
        stmt = stmt.where(Diary.event_id == event_id)
    stmt = stmt.order_by(Diary.id.desc()).limit(limit).offset(offset)
    return list(await session.scalars(stmt))


async def delete(session: AsyncSession, diary: Diary) -> None:
    await session.delete(diary)
    await session.flush()
