"""业务层：多轮人格对话。

每轮：
1. 校验会话归属和对方授权
2. 读取最近历史（服务端保存或客户端自带）
3. 用当前问题做 RAG 检索
4. 组装 system prompt：风格画像 + 典型发言 + 检索结果 + 规则
5. 调模型，保存消息

设计边界：
- 只读，不调用任何写工具（加清单、写日记以后再说）
- 不替对方做承诺
- 回复要像微信，不要写小作文
"""

import asyncio
import json
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.errors import AppError
from app.modules.agent import actions, tools
from app.modules.agent import repository as repo
from app.modules.agent.models import AgentConversation
from app.modules.agent.schemas import (
    ChatTurn,
    ConversationDetailOut,
    MessageOut,
)
from app.modules.ai import client as ai_client
from app.modules.ai import indexing, retrieval
from app.modules.couples.models import Couple
from app.modules.simta import repository as persona_repo
from app.modules.users.models import User

logger = structlog.get_logger("agent")

DISCLAIMER = "这是基于历史记录的模拟，不是 TA 本人。"

# 单一模式：既不扮完美的 TA，也不刻意学坏脾气 —— 温和但有据可依
PERSONA_RULES = (
    "要求：\n"
    "- 像微信聊天一样短，一次 1-3 句，不要写小作文\n"
    "- 保持 TA 的用词、标点、语气，比真实的 TA 更耐心一点\n"
    "- 只基于已知记录说话，不确定就说不确定，不要编造 TA 没表达过的态度\n"
    "- 可以给情绪支持，但绝对不要替 TA 做承诺（例如「我永远爱你」「我一定会改」）"
)


def _partner_id(couple: Couple, user_id: int) -> int:
    return couple.user2_id if couple.user1_id == user_id else couple.user1_id


async def create_conversation(
    session: AsyncSession,
    couple: Couple,
    user: User,
    title: str | None,
    persist: bool,
) -> AgentConversation:
    """新建一次对话。被模拟对象固定为当前用户的伴侣。"""
    now = datetime.now(UTC)
    conversation = await repo.create_conversation(
        session,
        couple_id=couple.id,
        owner_id=user.id,
        target_id=_partner_id(couple, user.id),
        title=title,
        persist=persist,
        expires_at=now + timedelta(days=settings.AGENT_RETENTION_DAYS),
    )
    await session.commit()
    await session.refresh(conversation)
    return conversation


async def get_detail(
    session: AsyncSession, couple: Couple, user: User, conversation_id: int
) -> ConversationDetailOut:
    conversation = await _get_owned(session, couple, user, conversation_id)
    rows = await repo.list_messages(session, conversation.id, 200)
    messages = [MessageOut.model_validate(row) for row in reversed(rows)]

    return ConversationDetailOut(
        id=conversation.id,
        target_id=conversation.target_id,
        title=conversation.title,
        persist=conversation.persist,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        expires_at=conversation.expires_at,
        messages=messages,
    )


async def memorize_conversation(
    session: AsyncSession,
    couple: Couple,
    user: User,
    conversation_id: int,
) -> int:
    """把这次会话切块，存成长期记忆（离开页面时调用）。

    重复调用是幂等的：块按 (day, seq) 覆盖，内容没变不会重新 embedding。
    """
    conversation = await _get_owned(session, couple, user, conversation_id)
    return await indexing.index_chat_memories(session, conversation.id)


async def validate_for_chat(
    session: AsyncSession,
    couple: Couple,
    user: User,
    conversation_id: int,
) -> AgentConversation:
    """对话前的统一校验：归属 + 对方授权。

    普通对话和流式对话都先走这里，避免两套判断逻辑。
    """
    conversation = await _get_owned(session, couple, user, conversation_id)

    consent = await persona_repo.get_consent(
        session, couple.id, conversation.target_id
    )
    if consent is None or not consent.authorized:
        raise AppError(
            "对方还没有授权把 TA 的数据用于模拟", code=14001, status_code=403
        )
    return conversation


async def _build_messages(
    session: AsyncSession,
    couple: Couple,
    user: User,
    conversation: AgentConversation,
    message: str,
    history: list[ChatTurn],
) -> list[dict]:
    """组装发给模型的完整 messages。"""
    target = await session.get(User, conversation.target_id)    #查询模拟Ta基础的信息
    nickname = target.nickname if target is not None else "TA"  #名字

    # TA 的记录 + 我自己的对话记忆：一次向量化、两路并发查，
    # 这两段以前是串行且各算一遍向量，光这一步就多花一秒多
    context_fragments, memory = await retrieval.collect_both(
        session,
        couple.id,
        conversation.target_id,
        user.id,
        query_text=message,
    )
    context = "\n".join(context_fragments)

    system = _system_prompt(nickname, user.nickname, context, memory)
    history_messages = await _load_history(session, conversation, history)      #拿到历史

    return (
        [{"role": "system", "content": system}]
        + history_messages
        + [{"role": "user", "content": message}]
    )


async def stream_reply(
    session: AsyncSession,
    couple_id: int,
    user_id: int,
    conversation_id: int,
    message: str,
    history: list[ChatTurn],
):
    """流式生成回复，支持工具调用。

    产出两类事件：
    - ("delta", 文本片段)：直接推给客户端
    - ("tool", {id, name, label, status})：工具执行状态

    工具调用和文本可以交替出现：模型先说一句、调工具、再接着说。
    """
    couple = await session.get(Couple, couple_id)   #去数据库查真实记录
    user = await session.get(User, user_id)         #去查数据库用户账户真实存在
    if couple is None or user is None:
        raise AppError("会话不存在", code=17001, status_code=404)

    conversation = await validate_for_chat(
        session, couple, user, conversation_id
    )   #进行校验
    messages = await _build_messages(
        session, couple, user, conversation, message, history
    )

    reply = ""
    for _ in range(settings.AGENT_MAX_TOOL_ROUNDS):
        tool_calls: list[dict] = []

        async for kind, payload in ai_client.stream_with_tools(
            messages, tools.TOOL_SCHEMAS
        ):
            if kind == "delta":
                reply += payload
                yield ("delta", payload)
            elif kind == "tool_calls":
                tool_calls = payload

        if not tool_calls:
            break

        # 把模型想调用的工具追加回对话，下一轮模型才能看到执行结果
        messages.append(
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": call["id"],
                        "type": "function",
                        "function": {
                            "name": call["name"],
                            "arguments": call["arguments"],
                        },
                    }
                    for call in tool_calls
                ],
            }
        )

        for call in tool_calls:
            # 只推状态和可读标签，不推工具的原始参数或结果
            yield (
                "tool",
                {
                    "id": call["id"],
                    "name": call["name"],
                    "label": tools.TOOL_LABELS.get(call["name"], "正在查询"),
                    "status": "running",
                },
            )

            try:
                args = json.loads(call["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {}

            output = await tools.execute_tool(
                call["name"],
                args,
                session=session,
                couple=couple,
                user=user,
                target_id=conversation.target_id,
                conversation=conversation,
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": output,
                }
            )
            yield (
                "tool",
                {
                    "id": call["id"],
                    "name": call["name"],
                    "status": "done",
                },
            )

            # 写工具不会直接执行，只返回一个待确认动作。
            # 把动作信息推给前端，由用户点击确认。
            try:
                parsed = json.loads(output)
            except json.JSONDecodeError:
                parsed = {}
            if parsed.get("status") == "pending_confirmation":
                yield (
                    "confirm",
                    {
                        "action_id": parsed["action_id"],
                        "type": parsed.get("type"),
                        "title": parsed.get("title"),
                        "category": parsed.get("category"),
                        "summary": parsed.get("summary"),
                        "expires_in": actions.EXPIRES_IN_SECONDS,
                    },
                )
    else:
        # 达到上限仍然没有给出文本，兜底一句，避免空回复
        fallback = "我想了一下，你再说具体一点？"
        reply += fallback
        yield ("delta", fallback)

    if conversation.persist:
        await repo.add_message(
            session, conversation_id=conversation.id, role="user", content=message
        )
        await repo.add_message(
            session, conversation_id=conversation.id, role="assistant", content=reply
        )
        conversation.expires_at = datetime.now(UTC) + timedelta(
            days=settings.AGENT_RETENTION_DAYS
        )
        await session.commit()

        # 每轮都把这一天的对话重切一次块（只写 PG，不调 embedding）。
        # 前端离开页面时再统一建向量 —— 这样即使前端没来得及触发
        # （杀进程、断网、请求时序），PG 里的记忆也是最新的。
        asyncio.create_task(_remember_blocks(conversation.id))


_memory_locks: dict[int, asyncio.Lock] = {}


def _memory_lock(conversation_id: int) -> asyncio.Lock:
    """同一条会话的记忆切块串行执行，避免并发写撞唯一约束。"""
    lock = _memory_locks.get(conversation_id)
    if lock is None:
        lock = asyncio.Lock()
        _memory_locks[conversation_id] = lock
    return lock


async def _remember_blocks(conversation_id: int) -> None:
    """后台把会话重切成记忆块（只写 PG，不建向量）。失败只记日志。"""
    try:
        async with _memory_lock(conversation_id):
            async with SessionLocal() as session:
                await indexing.index_chat_memories(
                    session, conversation_id, embed=False
                )
    except Exception as exc:  # noqa: BLE001 - 记忆失败不能影响聊天本身
        logger.warning(
            "agent.memory_blocks_failed",
            conversation_id=conversation_id,
            error=repr(exc),
        )


async def cleanup_expired(session: AsyncSession) -> int:
    """worker 定时任务：删除过期会话和消息。"""
    count = await repo.delete_expired(session, datetime.now(UTC))
    await session.commit()
    return count


async def _get_owned(
    session: AsyncSession, couple: Couple, user: User, conversation_id: int
) -> AgentConversation:
    """取出会话并校验归属。

    三个条件缺一不可：存在、属于当前关系、由当前用户发起。
    """
    conversation = await repo.get_conversation(session, conversation_id)
    if (
        conversation is None
        or conversation.couple_id != couple.id
        or conversation.owner_id != user.id
    ):
        raise AppError("会话不存在", code=17001, status_code=404)
    return conversation


async def _load_history(
    session: AsyncSession,
    conversation: AgentConversation,
    request_history: list[ChatTurn],
) -> list[dict[str, str]]:
    """加载最近的历史消息。

    - 服务端保存：从库里取最近 N 轮
    - 不保存：用客户端传来的 history
    """
    limit = settings.AGENT_MAX_HISTORY_TURNS * 2    #消息条数

    if not conversation.persist:    #没开持久化情况
        turns = request_history[-limit:]    #前端页面带上来的
        return [{"role": t.role, "content": t.content} for t in turns]  

    rows = await repo.list_messages(session, conversation.id, limit)
    return [{"role": row.role, "content": row.content} for row in reversed(rows)]


def _system_prompt(
    nickname: str,
    user_name: str,
    context: str,
    memory: list[str] | None = None,
) -> str:
    """组装人格 prompt。

    明确告诉模型：谁是它，谁是用户。
    否则检索到的对话里两个人都在说话，模型可能模仿错人。

    顺序：身份 -> 规则 -> TA 的记录 -> 你俩的对话 -> 边界
    """
    parts = [
        f"你正在扮演 {nickname}，正在和 {user_name} 聊天。",
        PERSONA_RULES,
        f"下面的记录里，「{nickname}」是你说的话，「{user_name}」是对方说的话。",
        f"只模仿「{nickname}」的语气，不要把对方的口吻当成自己的。",
    ]

    if context:
        parts.append(f"【TA 在类似话题下的真实记录】\n{context}")

    if memory:
        joined = "\n\n".join(memory)
        parts.append(f"【你俩之前聊过的片段】\n{joined}")

    parts.append(
        "需要查询事实时可以调用工具（记忆、关系、金币、商城、清单、每日一问）。"
        "只在确实需要时调用，不要为了调用而调用。"
    )
    parts.append(
        "只使用以上记录里的信息和口吻。不确定就说不确定，不要编造。"
        "不要替 TA 做承诺。"
    )
    parts.append(
        "【你俩之前聊过的片段】里的日期是那天的真实日期："
        "提到过去的约定或事情时要说清楚大概是哪时候（比如「上周你说…」），"
        "不要把它当成今天刚发生的事。"
    )
    return "\n\n".join(parts)
