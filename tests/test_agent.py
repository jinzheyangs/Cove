"""AI 对话：多轮记忆、授权校验、不保存模式、隔离、删除与过期清理。"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.errors import AppError
from app.modules.agent import service
from app.modules.agent.models import AgentMessage
from app.modules.agent.repository import get_conversation
from app.modules.agent.schemas import ChatTurn
from app.modules.ai import client as ai_client
from app.modules.simta import service as simta_service
from tests.helpers import seed_couple


async def _allow(session, couple, target):
    await simta_service.set_consent(session, couple, target, True)


async def test_chat_persists_user_and_assistant_messages(session, monkeypatch):
    a, b, couple = await seed_couple(session)
    await _allow(session, couple, b)
    conversation = await service.create_conversation(
        session, couple, a, "测试", persist=True
    )

    captured: dict = {}

    async def fake_chat(messages):
        captured["messages"] = messages
        return "在呢，怎么啦"

    monkeypatch.setattr(ai_client, "complete_chat", fake_chat)

    result = await service.chat(session, couple, a, conversation.id, "今天好累", [])

    assert result.reply == "在呢，怎么啦"
    assert result.disclaimer

    # system prompt 里带上了被模拟者的昵称
    assert "B" in captured["messages"][0]["content"]

    rows = list(
        await session.scalars(
            select(AgentMessage)
            .where(AgentMessage.conversation_id == conversation.id)
            .order_by(AgentMessage.id)
        )
    )
    assert [row.role for row in rows] == ["user", "assistant"]
    assert rows[0].content == "今天好累"


async def test_chat_requires_partner_consent(session, monkeypatch):
    a, _, couple = await seed_couple(session)
    conversation = await service.create_conversation(
        session, couple, a, None, persist=True
    )

    with pytest.raises(AppError) as exc:
        await service.chat(session, couple, a, conversation.id, "在吗", [])

    assert exc.value.code == 14001


async def test_history_is_included_in_next_turn(session, monkeypatch):
    a, b, couple = await seed_couple(session)
    await _allow(session, couple, b)
    conversation = await service.create_conversation(
        session, couple, a, None, persist=True
    )

    captured: dict = {}

    async def fake_chat(messages):
        captured["messages"] = messages
        return "回复一"

    monkeypatch.setattr(ai_client, "complete_chat", fake_chat)

    await service.chat(session, couple, a, conversation.id, "第一句", [])
    await service.chat(session, couple, a, conversation.id, "第二句", [])

    contents = [m["content"] for m in captured["messages"]]
    assert "第一句" in contents
    assert "回复一" in contents
    assert contents[-1] == "第二句"


async def test_persist_false_uses_request_history_and_stores_nothing(
    session, monkeypatch
):
    a, b, couple = await seed_couple(session)
    await _allow(session, couple, b)
    conversation = await service.create_conversation(
        session, couple, a, None, persist=False
    )

    captured: dict = {}

    async def fake_chat(messages):
        captured["messages"] = messages
        return "记得"

    monkeypatch.setattr(ai_client, "complete_chat", fake_chat)

    history = [
        ChatTurn(role="user", content="之前说的"),
        ChatTurn(role="assistant", content="我记得"),
    ]
    await service.chat(session, couple, a, conversation.id, "你还记得吗", history)

    contents = [m["content"] for m in captured["messages"]]
    assert "之前说的" in contents
    assert "我记得" in contents

    rows = list(
        await session.scalars(
            select(AgentMessage).where(
                AgentMessage.conversation_id == conversation.id
            )
        )
    )
    assert rows == []


async def test_conversation_is_isolated_per_user(session):
    a, b, couple = await seed_couple(session)
    conversation = await service.create_conversation(
        session, couple, a, None, persist=True
    )

    with pytest.raises(AppError) as exc:
        await service.get_detail(session, couple, b, conversation.id)

    assert exc.value.code == 17001


async def test_delete_conversation_removes_messages(session, monkeypatch):
    a, b, couple = await seed_couple(session)
    await _allow(session, couple, b)
    conversation = await service.create_conversation(
        session, couple, a, None, persist=True
    )

    async def fake_chat(messages):
        return "好"

    monkeypatch.setattr(ai_client, "complete_chat", fake_chat)
    await service.chat(session, couple, a, conversation.id, "在吗", [])

    conversation_id = conversation.id
    await service.delete_conversation(session, couple, a, conversation_id)

    assert await get_conversation(session, conversation_id) is None
    rows = list(
        await session.scalars(
            select(AgentMessage).where(AgentMessage.conversation_id == conversation_id)
        )
    )
    assert rows == []


async def test_cleanup_removes_expired_conversations(session):
    a, _, couple = await seed_couple(session)
    conversation = await service.create_conversation(
        session, couple, a, None, persist=True
    )
    conversation_id = conversation.id
    conversation.expires_at = datetime.now(UTC) - timedelta(days=1)
    await session.commit()

    count = await service.cleanup_expired(session)

    assert count == 1
    assert await get_conversation(session, conversation_id) is None
