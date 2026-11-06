"""Agent 工具：只读查询、工具调用循环、流式回复。"""

import json
from types import SimpleNamespace

from sqlalchemy import select

from app.modules.agent import service, tools
from app.modules.agent.models import AgentMessage
from app.modules.ai import client as ai_client
from app.modules.simta import service as simta_service
from app.modules.todos import service as todo_service
from app.modules.todos.schemas import TodoCreate
from tests.helpers import fund_user, seed_couple


async def test_get_couple_summary(session):
    a, b, couple = await seed_couple(session)

    output = json.loads(
        await tools.execute_tool(
            "get_couple_summary",
            {},
            session=session,
            couple=couple,
            user=a,
            target_id=b.id,
        )
    )

    assert output["days_together"] >= 0
    assert output["me"] == "A"
    assert output["partner"] == "B"


async def test_get_coin_balance(session):
    a, b, couple = await seed_couple(session)
    await fund_user(session, couple, a, 42)

    output = json.loads(
        await tools.execute_tool(
            "get_coin_balance",
            {},
            session=session,
            couple=couple,
            user=a,
            target_id=b.id,
        )
    )

    assert output["balance"] == 42


async def test_list_todos(session):
    a, b, couple = await seed_couple(session)
    await todo_service.create(
        session, couple, a, TodoCreate(category="想去的地方", title="一起看海")
    )

    output = json.loads(
        await tools.execute_tool(
            "list_todos",
            {},
            session=session,
            couple=couple,
            user=a,
            target_id=b.id,
        )
    )

    assert output["todos"][0]["title"] == "一起看海"


async def test_unknown_tool_returns_error(session):
    a, b, couple = await seed_couple(session)

    output = json.loads(
        await tools.execute_tool(
            "not_a_tool",
            {},
            session=session,
            couple=couple,
            user=a,
            target_id=b.id,
        )
    )

    assert "error" in output


async def test_search_memories(session, monkeypatch):
    a, b, couple = await seed_couple(session)

    async def fake_collect(session_, couple_id, target_id, query_text=None):
        return ["记忆片段"]

    monkeypatch.setattr(tools.retrieval, "collect_context", fake_collect)

    output = json.loads(
        await tools.execute_tool(
            "search_memories",
            {"query": "上次说的"},
            session=session,
            couple=couple,
            user=a,
            target_id=b.id,
        )
    )

    assert output["results"] == ["记忆片段"]


async def test_chat_executes_tool_and_continues(session, monkeypatch):
    a, b, couple = await seed_couple(session)
    await simta_service.set_consent(session, couple, b, True)
    conversation = await service.create_conversation(
        session, couple, a, None, persist=True
    )

    rounds: list[list[dict]] = []

    def make_tool_call():
        return SimpleNamespace(
            id="call-1",
            function=SimpleNamespace(name="get_coin_balance", arguments="{}"),
        )

    async def fake_complete(messages, tool_schemas):
        rounds.append(list(messages))
        if len(rounds) == 1:
            return SimpleNamespace(content="", tool_calls=[make_tool_call()])
        return SimpleNamespace(content="你现在有 0 个金币", tool_calls=None)

    monkeypatch.setattr(ai_client, "complete_with_tools", fake_complete)

    result = await service.chat(session, couple, a, conversation.id, "我有多少金币", [])

    assert result.reply == "你现在有 0 个金币"
    # 第二轮 messages 里应该已经有工具返回结果
    roles = [message["role"] for message in rounds[1]]
    assert "tool" in roles


async def test_stream_reply_yields_and_persists(session, monkeypatch):
    a, b, couple = await seed_couple(session)
    await simta_service.set_consent(session, couple, b, True)
    conversation = await service.create_conversation(
        session, couple, a, None, persist=True
    )

    async def fake_stream(messages):
        yield "在"
        yield "呢"

    monkeypatch.setattr(ai_client, "stream_chat", fake_stream)

    chunks = [
        chunk
        async for chunk in service.stream_reply(
            session, couple.id, a.id, conversation.id, "在吗", []
        )
    ]

    assert chunks == ["在", "呢"]

    rows = list(
        await session.scalars(
            select(AgentMessage)
            .where(AgentMessage.conversation_id == conversation.id)
            .order_by(AgentMessage.id)
        )
    )
    assert [row.role for row in rows] == ["user", "assistant"]
    assert rows[1].content == "在呢"
