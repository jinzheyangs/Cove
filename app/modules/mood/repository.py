"""数据访问层：每日心情的所有 SQL 都在这里。

约定：不 commit，事务由 service 控制。
"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.mood.models import MoodRecord


async def get_record(
    session: AsyncSession, couple_id: int, user_id: int, day: date
) -> MoodRecord | None:
    """取某人某天的心情。唯一约束保证最多一条。"""
    return await session.scalar(
        select(MoodRecord).where(
            MoodRecord.couple_id == couple_id,
            MoodRecord.user_id == user_id,
            MoodRecord.day == day,
        )
    )


async def upsert_record(
    session: AsyncSession,
    *,
    couple_id: int,
    user_id: int,
    day: date,
    mood: str | None,
    level: int,
    note: str | None,
) -> MoodRecord:
    """写入或修改当天心情。

    先查再决定 insert/update，而不是依赖 ON CONFLICT，
    因为修改时需要保留原有的 created_at。
    """
    existing = await get_record(session, couple_id, user_id, day)
    if existing is not None:
        existing.mood = mood
        existing.level = level
        existing.note = note
        await session.flush()
        return existing

    item = MoodRecord(
        couple_id=couple_id,
        user_id=user_id,
        day=day,
        mood=mood,
        level=level,
        note=note,
    )
    session.add(item)
    await session.flush()
    return item
