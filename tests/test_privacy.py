"""隐私：解绑、注销匿名化、数据导出。"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.core.errors import AppError
from app.modules.agent.models import (
    AgentConversation,
    AgentMessage,
    ChatImport,
    ChatMessage,
    PersonaProfile,
)
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


async def test_delete_account_purges_agent_and_chat_data(session):
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

    # 本人上传的导入 + 双方消息
    own_import = ChatImport(
        couple_id=couple.id,
        uploaded_by=a.id,
        filename="mine.jsonl",
        format="jsonl",
    )
    session.add(own_import)
    await session.flush()
    session.add_all(
        [
            ChatMessage(
                couple_id=couple.id,
                import_id=own_import.id,
                sender_id=a.id,
                sender_name="A",
                sent_at=datetime.now(UTC),
                content="A 的私聊",
                source_hash="hash-a-1",
            ),
            ChatMessage(
                couple_id=couple.id,
                import_id=own_import.id,
                sender_id=b.id,
                sender_name="B",
                sent_at=datetime.now(UTC),
                content="B 的私聊",
                source_hash="hash-b-1",
            ),
        ]
    )

    # 对方上传的导入，里面也有本人的发言
    partner_import = ChatImport(
        couple_id=couple.id,
        uploaded_by=b.id,
        filename="theirs.jsonl",
        format="jsonl",
    )
    session.add(partner_import)
    await session.flush()
    session.add_all(
        [
            ChatMessage(
                couple_id=couple.id,
                import_id=partner_import.id,
                sender_id=a.id,
                sender_name="A",
                sent_at=datetime.now(UTC),
                content="我在对方导入里的话",
                source_hash="hash-a-2",
            ),
            ChatMessage(
                couple_id=couple.id,
                import_id=partner_import.id,
                sender_id=b.id,
                sender_name="B",
                sent_at=datetime.now(UTC),
                content="对方自己的话",
                source_hash="hash-b-2",
            ),
        ]
    )

    # 派生的画像与刷新令牌
    session.add(
        PersonaProfile(
            couple_id=couple.id,
            user_id=a.id,
            style_summary="说话简短",
            samples_json="[]",
            stats={},
        )
    )
    await user_service.issue_tokens(session, a)
    await session.commit()

    a_id = a.id
    await privacy_service.delete_account(session, a, TEST_PASSWORD)

    # 本人的 Agent 会话、画像、刷新令牌都清掉
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
    assert await _count(session, PersonaProfile) == 0
    assert (
        await session.scalar(
            select(func.count())
            .select_from(RefreshToken)
            .where(RefreshToken.user_id == a_id)
        )
        == 0
    )

    # 本人上传的导入整条删除；对方导入保留，但本人的发言被删掉
    assert await _count(session, ChatImport) == 1
    remaining = await session.get(ChatImport, partner_import.id)
    assert remaining is not None
    assert (
        await session.scalar(
            select(func.count())
            .select_from(ChatMessage)
            .where(ChatMessage.sender_id == a_id)
        )
        == 0
    )
    assert (
        await session.scalar(
            select(func.count())
            .select_from(ChatMessage)
            .where(ChatMessage.import_id == partner_import.id)
        )
        == 1
    )


async def test_export_includes_own_content(session):
    a, _, couple = await seed_couple(session)
    await diary_service.create(session, couple, a, DiaryCreate(content="要导出的日记"))

    data = await privacy_service.export_data(session, a)

    assert data["profile"]["id"] == a.id
    assert data["diaries"][0]["content"] == "要导出的日记"
    assert data["couple"]["id"] == couple.id
