"""数据访问层：每日一问的所有 SQL 都在这里。

约定：不 commit，事务由 service 控制。
"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.daily.models import DailyAnswer


async def get_answer(
    session: AsyncSession, couple_id: int, user_id: int, day: date
) -> DailyAnswer | None:
    """取某人某天的回答。唯一约束保证最多一条。"""
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
    """写入或修改当天回答。

    先查再决定 insert/update，而不是依赖 ON CONFLICT，
    因为修改时需要保留原有的 created_at。
    """
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
