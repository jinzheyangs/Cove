"""数据访问层：每日一问的所有 SQL 都在这里。"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.daily.models import DailyAnswer


async def get_answer(
    session: AsyncSession, couple_id: int, user_id: int, day: date
) -> DailyAnswer | None:
    return await session.scalar(
        select(DailyAnswer).where(
            DailyAnswer.couple_id == couple_id,
            DailyAnswer.user_id == user_id,
            DailyAnswer.day == day,
        )
    )


async def upsert_answer(
    session: AsyncSession,
    *,
    couple_id: int,
    user_id: int,
    day: date,
    question: str,
    answer: str,
) -> DailyAnswer:
    existing = await get_answer(session, couple_id, user_id, day)
    if existing is not None:
        existing.answer = answer
        await session.flush()
        return existing

    item = DailyAnswer(
        couple_id=couple_id, user_id=user_id, day=day, question=question, answer=answer
    )
    session.add(item)
    await session.flush()
    return item
