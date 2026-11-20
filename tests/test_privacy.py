"""隐私：解绑、注销匿名化。"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.core.errors import AppError
from app.modules.agent.models import AgentConversation, AgentMessage, ChatMemory
from app.modules.couples import service as couple_service
from app.modules.diaries import service as diary_service
from app.modules.diaries.schemas import DiaryCreate
from app.modules.privacy import service as privacy_service
from app.modules.users import service as user_service
from app.modules.users.models import RefreshToken, User
from tests.helpers import TEST_PASSWORD, seed_couple


async def _count(session, model) -> int:
    return await session.scalar(select(func.count()).select_from(model))


async def test_unbind_requires_confirmation(session):
    a, _, couple = await seed_couple(session)

    with pytest.raises(AppError) as exc:
        await couple_service.unbind(session, couple, a, confirm=False)

    assert exc.value.code == 2008


async def test_unbind_marks_couple(session):
    a, _, couple = await seed_couple(session)

    updated = await couple_service.unbind(session, couple, a, confirm=True)

    assert updated.status == "unbound"
    assert updated.unbound_at is not None


async def test_delete_account_rejects_wrong_password(session):
    a, _, _ = await seed_couple(session)

    with pytest.raises(AppError) as exc:
        await privacy_service.delete_account(session, a, "wrong")

    assert exc.value.code == 15001


async def test_delete_account_anonymizes_and_purges(session):
    a, _, couple = await seed_couple(session)
    await diary_service.create(session, couple, a, DiaryCreate(content="我的日记"))
    a_id = a.id

    await privacy_service.delete_account(session, a, TEST_PASSWORD)

    user = await session.get(User, a_id)
    assert user is not None
    assert user.deleted_at is not None
    assert user.nickname == "已注销"
    assert user.phone == f"deleted-{a_id}"

    assert await diary_service.list_diaries(session, couple) == []


async def test_delete_account_purges_agent_data(session):
    a, b, couple = await seed_couple(session)

    # Agent 会话 + 消息
    conversation = AgentConversation(
        couple_id=couple.id,
        owner_id=a.id,
        target_id=b.id,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    session.add(conversation)
    await session.flush()
    session.add(
        AgentMessage(
            conversation_id=conversation.id,
            role="user",
            content="只有我知道的话",
        )
    )
    await user_service.issue_tokens(session, a)
    await session.commit()

    a_id = a.id
    await privacy_service.delete_account(session, a, TEST_PASSWORD)

    # 本人的 Agent 会话、消息、刷新令牌都清掉
    assert (
        await session.scalar(
            select(func.count())
            .select_from(AgentConversation)
            .where(AgentConversation.owner_id == a_id)
        )
        == 0
    )
    assert (
        await session.scalar(
            select(func.count())
            .select_from(AgentMessage)
            .where(AgentMessage.conversation_id == conversation.id)
        )
        == 0
    )
    assert (
        await session.scalar(
            select(func.count())
            .select_from(RefreshToken)
            .where(RefreshToken.user_id == a_id)
        )
        == 0
    )


async def test_delete_account_purges_chat_memory(session):
    """注销之后「我跟分身聊过什么」不该留在库里。

    chat_memories 故意没挂会话外键（会话 30 天清、记忆要留更久），
    所以它只能靠注销流程显式清理。
    """
    a, b, couple = await seed_couple(session)
    session.add(
        ChatMemory(
            couple_id=couple.id,
            owner_id=a.id,
            target_id=b.id,
            conversation_id=1,
            day=datetime.now(UTC).date(),
            seq=0,
            text="今天和分身聊了很多",
        )
    )
    await session.commit()

    a_id = a.id
    await privacy_service.delete_account(session, a, TEST_PASSWORD)

    assert (
        await session.scalar(
            select(func.count())
            .select_from(ChatMemory)
            .where(ChatMemory.owner_id == a_id)
        )
        == 0
    )
