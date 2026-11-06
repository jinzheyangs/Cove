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

import json
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError
from app.modules.agent import repository as repo
from app.modules.agent import tools
from app.modules.agent.models import AgentConversation, PersonaProfile
from app.modules.agent.schemas import (
    ChatTurn,
    ConversationDetailOut,
    MessageOut,
)
from app.modules.ai import client as ai_client
from app.modules.ai import retrieval
from app.modules.couples.models import Couple
from app.modules.simta import repository as persona_repo
from app.modules.users.models import User

DISCLAIMER = "这是基于历史记录的模拟，不是 TA 本人。"

FAITHFUL_RULES = (
    "要求：\n"
    "- 像微信聊天一样短，一次 1-3 句，不要写小作文\n"
    "- 保持 TA 的用词、标点、语气\n"
    "- 只基于已知记录说话，不确定就说不确定\n"
    "- 不要替 TA 许诺或做决定"
)

IDEALIZED_RULES = (
    "要求：\n"
    "- 像微信聊天一样短，一次 1-3 句\n"
    "- 比真实的 TA 更耐心、更温和\n"
    "- 可以给情绪支持\n"
    "- 绝对不要替 TA 做承诺（例如「我永远爱你」「我一定会改」）"
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


async def list_conversations(
    session: AsyncSession, user: User
) -> list[AgentConversation]:
    return await repo.list_by_owner(session, user.id)


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


async def delete_conversation(
    session: AsyncSession, couple: Couple, user: User, conversation_id: int
) -> None:
    """删除会话及其全部消息。"""
    conversation = await _get_owned(session, couple, user, conversation_id)
    await repo.delete_messages(session, conversation.id)
    await repo.delete_conversation(session, conversation)
    await session.commit()


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

    # TA 的风格设置：忠实 / 理想化
    fidelity_row = await persona_repo.get_settings(session, couple.id, user.id)
    fidelity = fidelity_row.fidelity if fidelity_row else "faithful"

    # 被模拟 TA 的完整画像（口头禅、句长、标点习惯）
    profile = await repo.get_profile(session, couple.id, conversation.target_id)

    fragments = await retrieval.collect_context(
        session, couple.id, conversation.target_id, query_text=message
    )   #拿到记忆字符串列表
    context = "\n".join(fragments)  #得到字符串

    system = _system_prompt(nickname, user.nickname, fidelity, profile, context)    #组装提示词
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
    couple = await session.get(Couple, couple_id)
    user = await session.get(User, user_id)
    if couple is None or user is None:
        raise AppError("会话不存在", code=17001, status_code=404)

    conversation = await validate_for_chat(
        session, couple, user, conversation_id
    )
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
    fidelity: str,
    profile: PersonaProfile | None,
    context: str,
) -> str:
    """组装人格 prompt。

    明确告诉模型：谁是它，谁是用户。
    否则检索到的对话里两个人都在说话，模型可能模仿错人。

    顺序：身份 -> 规则 -> 风格画像 -> 典型发言 -> 检索上下文 -> 边界
    """
    parts = [
        f"你正在扮演 {nickname}，正在和 {user_name} 聊天。",
        IDEALIZED_RULES if fidelity == "idealized" else FAITHFUL_RULES,
        f"下面的记录里，「{nickname}」是你说的话，「{user_name}」是对方说的话。",
        f"只模仿「{nickname}」的语气，不要把对方的口吻当成自己的。",
    ]

    if profile and profile.style_summary:
        parts.append(f"【风格画像】\n{profile.style_summary}")

    if profile and profile.samples_json:
        try:
            samples = json.loads(profile.samples_json)
        except json.JSONDecodeError:
            samples = []
        if samples:
            lines = "\n".join(f"- {sample}" for sample in samples[:10])
            parts.append(f"【TA 的典型发言】\n{lines}")

    if context:
        parts.append(f"【TA 在类似话题下的真实记录】\n{context}")

    parts.append(
        "需要查询事实时可以调用工具（记忆、关系、金币、商城、清单、每日一问）。"
        "只在确实需要时调用，不要为了调用而调用。"
    )
    parts.append(
        "只使用以上记录里的信息和口吻。不确定就说不确定，不要编造。"
        "不要替 TA 做承诺。"
    )
    return "\n\n".join(parts)
