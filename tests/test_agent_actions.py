"""写操作确认流程：提议、确认、取消、越权、过期与流式事件。"""

import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.core.errors import AppError
from app.modules.agent import actions, service, tools
from app.modules.agent.models import AgentAction
from app.modules.ai import client as ai_client
from app.modules.simta import service as simta_service
from app.modules.todos.models import TodoItem
from tests.helpers import seed_couple


async def _conversation(session, couple, user):
    return await service.create_conversation(session, couple, user, None, persist=True)


async def _pending_todo(session, couple, user, conversation):
    return await actions.create_pending(
        session,
        conversation,
        user,
        "create_todo",
        {"title": "一起看海", "category": "想去的地方", "description": None},
    )


async def test_propose_creates_pending_action(session):
    a, b, couple = await seed_couple(session)
    conversation = await _conversation(session, couple, a)

    output = await tools.execute_tool(
        "propose_create_todo",
        {"title": "一起看海", "category": "想去的地方"},
        session=session,
        couple=couple,
        user=a,
        target_id=b.id,
        conversation=conversation,
    )
    data = json.loads(output)

    assert data["status"] == "pending_confirmation"
    assert data["type"] == "create_todo"

    action = await session.get(AgentAction, data["action_id"])
    assert action is not None
    assert action.status == "pending"
    assert action.user_id == a.id


async def test_confirm_creates_todo_once(session):
    a, _, couple = await seed_couple(session)
    conversation = await _conversation(session, couple, a)
    action = await _pending_todo(session, couple, a, conversation)

    confirmed, result = await actions.confirm(session, couple, a, action.id)
    assert confirmed.status == "confirmed"
    assert result["todo_id"]

    # 重复确认是幂等的，不会多写一条
    again, same_result = await actions.confirm(session, couple, a, action.id)
    assert again.status == "confirmed"
    assert same_result["todo_id"] == result["todo_id"]

    count = await session.scalar(select(func.count()).select_from(TodoItem))
    assert count == 1


async def test_cancel_does_not_create_todo(session):
    a, _, couple = await seed_couple(session)
    conversation = await _conversation(session, couple, a)
    action = await _pending_todo(session, couple, a, conversation)

    cancelled = await actions.cancel(session, couple, a, action.id)

    assert cancelled.status == "cancelled"
    count = await session.scalar(select(func.count()).select_from(TodoItem))
    assert count == 0


async def test_cannot_confirm_another_users_action(session):
    a, b, couple = await seed_couple(session)
    conversation = await _conversation(session, couple, a)
    action = await _pending_todo(session, couple, a, conversation)

    with pytest.raises(AppError) as exc:
        await actions.confirm(session, couple, b, action.id)

    assert exc.value.code == 17011


async def test_expired_action_is_rejected(session):
    a, _, couple = await seed_couple(session)
    conversation = await _conversation(session, couple, a)
    action = await _pending_todo(session, couple, a, conversation)
    action.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    await session.commit()

    with pytest.raises(AppError) as exc:
        await actions.confirm(session, couple, a, action.id)

    assert exc.value.code == 17010
    await session.refresh(action)
    assert action.status == "expired"


async def test_stream_emits_confirm_event_and_does_not_write_yet(
    session, monkeypatch
):
    a, b, couple = await seed_couple(session)
    await simta_service.set_consent(session, couple, b, True)
    conversation = await _conversation(session, couple, a)

    rounds: list[list[dict]] = []

    async def fake_stream(messages, tool_schemas):
        rounds.append(list(messages))
        if len(rounds) == 1:
            yield (
                "tool_calls",
                [
                    {
                        "id": "call-1",
                        "name": "propose_create_todo",
                        "arguments": json.dumps(
                            {"title": "一起看海", "category": "想去的地方"},
                            ensure_ascii=False,
                        ),
                    }
                ],
            )
        else:
            yield ("delta", "好的，确认一下")

    monkeypatch.setattr(ai_client, "stream_with_tools", fake_stream)

    confirm_events: list[dict] = []
    async for kind, payload in service.stream_reply(
        session, couple.id, a.id, conversation.id, "帮我加一条看海", []
    ):
        if kind == "confirm":
            confirm_events.append(payload)

    assert len(confirm_events) == 1
    assert confirm_events[0]["title"] == "一起看海"

    # 还没点确认，清单不应该被写入
    count = await session.scalar(select(func.count()).select_from(TodoItem))
    assert count == 0

    await actions.confirm(session, couple, a, confirm_events[0]["action_id"])
    count = await session.scalar(select(func.count()).select_from(TodoItem))
    assert count == 1


async def test_delete_conversation_removes_actions(session):
    a, _, couple = await seed_couple(session)
    conversation = await _conversation(session, couple, a)
    action = await _pending_todo(session, couple, a, conversation)
    action_id = action.id

    await service.delete_conversation(session, couple, a, conversation.id)

    assert await session.get(AgentAction, action_id) is None
