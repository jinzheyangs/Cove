"""数据访问层：争吵会话的所有 SQL 都在这里。

约定：不 commit，事务由 service 控制。
"""

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
    """取当前未关闭的会话。

    ongoing / cooling / reviewing 都算“进行中”，
    同一对伴侣同时只能有一个。
    """
    return await session.scalar(
        select(ConflictSession).where(
            ConflictSession.couple_id == couple_id,
            ConflictSession.status.in_(["ongoing", "cooling", "reviewing"]),
        )
    )


async def create_session(session: AsyncSession, couple_id: int) -> ConflictSession:
    """创建会话，初始状态 ongoing。"""
    conflict = ConflictSession(couple_id=couple_id, status="ongoing")
    session.add(conflict)
    await session.flush()
    return conflict


async def get_session(session: AsyncSession, session_id: int) -> ConflictSession | None:
    """按主键读取。越权判断在 service 层。"""
    return await session.get(ConflictSession, session_id)


async def add_message(
    session: AsyncSession, *, session_id: int, user_id: int, content: str, flagged: bool
) -> ConflictMessage:
    """保存消息。content 由 EncryptedText 自动加密。"""
    message = ConflictMessage(
        session_id=session_id, user_id=user_id, content=content, flagged=flagged
    )
    session.add(message)
    await session.flush()
    return message


async def list_messages(
    session: AsyncSession, session_id: int
) -> list[ConflictMessage]:
    """按时间正序取全部消息。"""
    stmt = (
        select(ConflictMessage)
        .where(ConflictMessage.session_id == session_id)
        .order_by(ConflictMessage.id)
    )
    return list(await session.scalars(stmt))


async def get_review(
    session: AsyncSession, session_id: int, user_id: int
) -> ConflictReview | None:
    """查某人在这条会话里的复盘。用于判断是新增还是修改。"""
    return await session.scalar(
        select(ConflictReview).where(
            ConflictReview.session_id == session_id,
            ConflictReview.user_id == user_id,
        )
    )


async def list_reviews(session: AsyncSession, session_id: int) -> list[ConflictReview]:
    """取这条会话的全部复盘。"""
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
    """插入复盘。两个字段都加密。"""
    review = ConflictReview(
        session_id=session_id,
        user_id=user_id,
        want_to_be_understood=want,
        heard_partner_need=heard,
    )
    session.add(review)
    await session.flush()
    return review


async def count_reviews(
    session: AsyncSession, session_id: int, couple_user_ids: list[int]
) -> int:
    """统计这条会话里双方提交了几份复盘。

    限制在关系双方的 id 内，避免把历史脏数据算进来。
    """
    stmt = select(ConflictReview).where(
        ConflictReview.session_id == session_id,
        or_(*[ConflictReview.user_id == uid for uid in couple_user_ids]),
    )
    return len(list(await session.scalars(stmt)))
