"""数据访问层：争吵会话的所有 SQL 都在这里。"""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.conflicts.models import (
    ConflictMessage,
    ConflictReview,
    ConflictSession,
)


async def get_active_session(
    session: AsyncSession, couple_id: int
) -> ConflictSession | None:
    return await session.scalar(
        select(ConflictSession).where(
            ConflictSession.couple_id == couple_id,
            ConflictSession.status.in_(["ongoing", "cooling", "reviewing"]),
        )
    )


async def create_session(session: AsyncSession, couple_id: int) -> ConflictSession:
    conflict = ConflictSession(couple_id=couple_id, status="ongoing")
    session.add(conflict)
    await session.flush()
    return conflict


async def get_session(session: AsyncSession, session_id: int) -> ConflictSession | None:
    return await session.get(ConflictSession, session_id)


async def add_message(
    session: AsyncSession, *, session_id: int, user_id: int, content: str, flagged: bool
) -> ConflictMessage:
    message = ConflictMessage(
        session_id=session_id, user_id=user_id, content=content, flagged=flagged
    )
    session.add(message)
    await session.flush()
    return message


async def list_messages(
    session: AsyncSession, session_id: int
) -> list[ConflictMessage]:
    stmt = (
        select(ConflictMessage)
        .where(ConflictMessage.session_id == session_id)
        .order_by(ConflictMessage.id)
    )
    return list(await session.scalars(stmt))


async def get_review(
    session: AsyncSession, session_id: int, user_id: int
) -> ConflictReview | None:
    return await session.scalar(
        select(ConflictReview).where(
            ConflictReview.session_id == session_id,
            ConflictReview.user_id == user_id,
        )
    )


async def list_reviews(session: AsyncSession, session_id: int) -> list[ConflictReview]:
    stmt = select(ConflictReview).where(ConflictReview.session_id == session_id)
    return list(await session.scalars(stmt))


async def add_review(
    session: AsyncSession,
    *,
    session_id: int,
    user_id: int,
    want: str,
    heard: str,
) -> ConflictReview:
    review = ConflictReview(
        session_id=session_id,
        user_id=user_id,
        want_to_be_understood=want,
        heard_partner_need=heard,
    )
    session.add(review)
    await session.flush()
    return review


async def count_reviews(session: AsyncSession, session_id: int, couple_user_ids: list[int]) -> int:
    stmt = select(ConflictReview).where(
        ConflictReview.session_id == session_id,
        or_(*[ConflictReview.user_id == uid for uid in couple_user_ids]),
    )
    return len(list(await session.scalars(stmt)))
