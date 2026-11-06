"""数据访问层：AI 对话的会话、消息和风格画像。

约定：不 commit，事务由 service 控制。
"""

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agent.models import AgentConversation, AgentMessage, PersonaProfile


async def create_conversation(
    session: AsyncSession,
    *,
    couple_id: int,
    owner_id: int,
    target_id: int,
    title: str | None,
    persist: bool,
    expires_at: datetime,
) -> AgentConversation:
    conversation = AgentConversation(
        couple_id=couple_id,
        owner_id=owner_id,
        target_id=target_id,
        title=title,
        persist=persist,
        expires_at=expires_at,
    )
    session.add(conversation)
    await session.flush()
    return conversation


async def get_conversation(
    session: AsyncSession, conversation_id: int
) -> AgentConversation | None:
    return await session.get(AgentConversation, conversation_id)


async def list_by_owner(
    session: AsyncSession, owner_id: int
) -> list[AgentConversation]:
    stmt = (
        select(AgentConversation)
        .where(AgentConversation.owner_id == owner_id)
        .order_by(AgentConversation.updated_at.desc())
    )
    return list(await session.scalars(stmt))


async def add_message(
    session: AsyncSession, *, conversation_id: int, role: str, content: str
) -> AgentMessage:
    message = AgentMessage(
        conversation_id=conversation_id, role=role, content=content
    )
    session.add(message)
    await session.flush()
    return message


async def list_messages(
    session: AsyncSession, conversation_id: int, limit: int
) -> list[AgentMessage]:
    """取最近的 limit 条，按 id 倒序。

    调用方需要正序时自己 reverse，避免在这里做两次查询。
    """
    stmt = (
        select(AgentMessage)
        .where(AgentMessage.conversation_id == conversation_id)
        .order_by(AgentMessage.id.desc())
        .limit(limit)
    )
    return list(await session.scalars(stmt))


async def delete_messages(session: AsyncSession, conversation_id: int) -> None:
    await session.execute(
        delete(AgentMessage).where(AgentMessage.conversation_id == conversation_id)
    )
    await session.flush()


async def delete_conversation(
    session: AsyncSession, conversation: AgentConversation
) -> None:
    await session.delete(conversation)
    await session.flush()


async def get_profile(
    session: AsyncSession, couple_id: int, user_id: int
) -> PersonaProfile | None:
    return await session.scalar(
        select(PersonaProfile).where(
            PersonaProfile.couple_id == couple_id,
            PersonaProfile.user_id == user_id,
        )
    )


async def delete_expired(session: AsyncSession, now: datetime) -> int:
    """删除过期会话及其消息，返回删除的会话数。"""
    expired_ids = select(AgentConversation.id).where(
        AgentConversation.expires_at < now
    )
    await session.execute(
        delete(AgentMessage).where(AgentMessage.conversation_id.in_(expired_ids))
    )
    result = await session.execute(
        delete(AgentConversation).where(AgentConversation.expires_at < now)
    )
    return result.rowcount or 0
