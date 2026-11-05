"""数据访问层：询问中心的所有 SQL 都在这里。

约定：不 commit，事务由 service 控制。
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.inquiries.models import (
    InquiryInput,
    InquirySession,
    InquirySupplement,
)


async def create_session(session: AsyncSession, couple_id: int, question: str) -> InquirySession:
    """创建会话，初始状态 collecting。"""
    item = InquirySession(couple_id=couple_id, question=question)
    session.add(item)
    await session.flush()
    return item


async def get_session(session: AsyncSession, session_id: int) -> InquirySession | None:
    """按主键读取。越权判断在 service 层。"""
    return await session.get(InquirySession, session_id)


async def get_input(
    session: AsyncSession, session_id: int, user_id: int
) -> InquiryInput | None:
    """查某人在某次询问里的输入。"""
    return await session.scalar(
        select(InquiryInput).where(
            InquiryInput.session_id == session_id, InquiryInput.user_id == user_id
        )
    )


async def list_inputs(session: AsyncSession, session_id: int) -> list[InquiryInput]:
    """取这次询问的全部输入。

    按 id 正序，保证生成 prompt 时顺序稳定。
    """
    stmt = (
        select(InquiryInput)
        .where(InquiryInput.session_id == session_id)
        .order_by(InquiryInput.id)
    )
    return list(await session.scalars(stmt))


async def upsert_input(
    session: AsyncSession, session_id: int, user_id: int, content: str
) -> InquiryInput:
    """写入或修改自己的输入。

    collecting 阶段可以反复修改，所以用 upsert 而不是 insert。
    """
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
    """追加一条补充意见。"""
    item = InquirySupplement(
        session_id=session_id, user_id=user_id, content=content
    )
    session.add(item)
    await session.flush()
    return item


async def list_supplements(
    session: AsyncSession, session_id: int
) -> list[InquirySupplement]:
    """取全部补充意见，按时间正序。"""
    stmt = (
        select(InquirySupplement)
        .where(InquirySupplement.session_id == session_id)
        .order_by(InquirySupplement.id)
    )
    return list(await session.scalars(stmt))
