"""数据访问层：询问中心的所有 SQL 都在这里。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.inquiries.models import (
    InquiryInput,
    InquirySession,
    InquirySupplement,
)


async def create_session(session: AsyncSession, couple_id: int, question: str) -> InquirySession:
    item = InquirySession(couple_id=couple_id, question=question)
    session.add(item)
    await session.flush()
    return item


async def get_session(session: AsyncSession, session_id: int) -> InquirySession | None:
    return await session.get(InquirySession, session_id)


async def get_input(
    session: AsyncSession, session_id: int, user_id: int
) -> InquiryInput | None:
    return await session.scalar(
        select(InquiryInput).where(
            InquiryInput.session_id == session_id, InquiryInput.user_id == user_id
        )
    )


async def list_inputs(session: AsyncSession, session_id: int) -> list[InquiryInput]:
    stmt = (
        select(InquiryInput)
        .where(InquiryInput.session_id == session_id)
        .order_by(InquiryInput.id)
    )
    return list(await session.scalars(stmt))


async def upsert_input(
    session: AsyncSession, session_id: int, user_id: int, content: str
) -> InquiryInput:
    existing = await get_input(session, session_id, user_id)
    if existing is not None:
        existing.content = content
        await session.flush()
        return existing
    item = InquiryInput(session_id=session_id, user_id=user_id, content=content)
    session.add(item)
    await session.flush()
    return item


async def add_supplement(
    session: AsyncSession, session_id: int, user_id: int, content: str
) -> InquirySupplement:
    item = InquirySupplement(
        session_id=session_id, user_id=user_id, content=content
    )
    session.add(item)
    await session.flush()
    return item


async def list_supplements(
    session: AsyncSession, session_id: int
) -> list[InquirySupplement]:
    stmt = (
        select(InquirySupplement)
        .where(InquirySupplement.session_id == session_id)
        .order_by(InquirySupplement.id)
    )
    return list(await session.scalars(stmt))
