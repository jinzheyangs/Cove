"""Agent 可以调用的工具。

读工具：查记忆、关系、金币、商城、清单、每日一问，直接执行。
写工具：只创建「待确认动作」，用户点确认后才真正写入。

每个工具返回 JSON 字符串，直接作为 role=tool 的消息回给模型。
"""

import json
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agent import actions
from app.modules.agent.models import AgentConversation
from app.modules.ai import retrieval
from app.modules.coins import repository as coin_repo
from app.modules.couples.models import Couple
from app.modules.daily import service as daily_service
from app.modules.mall import repository as mall_repo
from app.modules.todos import repository as todo_repo
from app.modules.users.models import User

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_memories",
            "description": (
                "检索伴侣过去写过的日记、争吵复盘和聊天片段。"
                "适合回答“我们上次说过什么”“TA 怎么想的”这类问题。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "要检索的内容或问题"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_couple_summary",
            "description": "查询这段关系的基本信息：在一起多少天、双方昵称、绑定时间。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_coin_balance",
            "description": "查询当前用户的金币余额。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_mall_items",
            "description": "列出商城里已上架、可以兑换的商品和服务。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_todos",
            "description": "列出共同清单里还没完成的事项。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_today_question",
            "description": "获取今天的每日一问，以及当前用户有没有回答。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_create_todo",
            "description": (
                "当用户明确要求把某件事加入共同清单时，提议创建一条待确认的清单项。"
                "不要直接创建——用户确认后才会真的写入。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "清单标题"},
                    "category": {
                        "type": "string",
                        "description": (
                            "分类：想去的地方 / 想一起学的技能 / "
                            "想改掉的习惯 / 想实现的约定"
                        ),
                    },
                    "description": {"type": "string", "description": "补充说明，可选"},
                },
                "required": ["title"],
            },
        },
    },
]


async def _search_memories(session, couple, user, target_id, args) -> dict:
    query = str(args.get("query", "")).strip()
    if not query:
        return {"error": "query 不能为空"}
    docs = await retrieval.collect_context(
        session, couple.id, target_id, query_text=query
    )
    return {"results": docs}


async def _get_couple_summary(session, couple, user, target_id, args) -> dict:
    partner = await session.get(User, target_id)
    days = max(0, (datetime.now(UTC) - couple.bind_at).days)
    return {
        "days_together": days,
        "bind_at": couple.bind_at.isoformat(),
        "me": user.nickname,
        "partner": partner.nickname if partner is not None else None,
    }


async def _get_coin_balance(session, couple, user, target_id, args) -> dict:
    balance = await coin_repo.get_balance(session, user.id)
    return {"balance": balance}


async def _list_mall_items(session, couple, user, target_id, args) -> dict:
    items = await mall_repo.list_approved(session, couple.id)
    return {
        "items": [
            {
                "id": item.id,
                "title": item.title,
                "price": item.approved_price or item.price_coins,
            }
            for item in items[:20]
        ]
    }


async def _list_todos(session, couple, user, target_id, args) -> dict:
    todos = await todo_repo.list_items(
        session, couple.id, item_type="shared", status="pending"
    )
    return {
        "todos": [
            {"id": todo.id, "title": todo.title, "category": todo.category}
            for todo in todos[:20]
        ]
    }


async def _get_today_question(session, couple, user, target_id, args) -> dict:
    view = await daily_service.today_view(session, couple, user)
    return {
        "question": view.question,
        "answered": view.my_answer is not None,
    }


async def _propose_create_todo(
    session, couple, user, conversation, args
) -> dict:
    """创建一个待确认的清单动作，不直接写清单。"""
    if conversation is None:
        return {"error": "缺少会话上下文"}

    title = str(args.get("title", "")).strip()
    if not title:
        return {"error": "title 不能为空"}

    category = str(args.get("category") or "想实现的约定").strip()
    description = args.get("description")

    action = await actions.create_pending(
        session,
        conversation,
        user,
        "create_todo",
        {
            "title": title,
            "category": category,
            "description": description,
        },
    )
    return {
        "status": "pending_confirmation",
        "type": "create_todo",
        "action_id": action.id,
        "title": title,
        "category": category,
    }


# 流式对话里展示给用户的可读状态，不带任何工具结果
TOOL_LABELS = {
    "search_memories": "正在查记忆",
    "get_couple_summary": "正在查关系信息",
    "get_coin_balance": "正在查金币",
    "list_mall_items": "正在查商城",
    "list_todos": "正在查清单",
    "get_today_question": "正在查今日一问",
    "propose_create_todo": "准备添加清单",
}


_HANDLERS = {
    "search_memories": _search_memories,
    "get_couple_summary": _get_couple_summary,
    "get_coin_balance": _get_coin_balance,
    "list_mall_items": _list_mall_items,
    "list_todos": _list_todos,
    "get_today_question": _get_today_question,
}


async def execute_tool(
    name: str,
    args: dict,
    *,
    session: AsyncSession,
    couple: Couple,
    user: User,
    target_id: int,
    conversation: AgentConversation | None = None,
) -> str:
    """执行工具，返回 JSON 字符串。

    读工具直接执行；写工具只创建待确认动作。
    工具内部异常不会中断对话，转成 error 字段让模型自己处理。
    """
    try:
        if name == "propose_create_todo":
            result = await _propose_create_todo(
                session, couple, user, conversation, args
            )
        else:
            handler = _HANDLERS.get(name)
            if handler is None:
                return json.dumps({"error": f"未知工具: {name}"}, ensure_ascii=False)
            result = await handler(session, couple, user, target_id, args)
    except Exception as exc:  # noqa: BLE001 - 工具失败不应中断对话
        return json.dumps({"error": str(exc)}, ensure_ascii=False)

    return json.dumps(result, ensure_ascii=False, default=str)
