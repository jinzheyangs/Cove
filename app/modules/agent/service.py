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
from app.modules.agent.models import AgentConversation, PersonaProfile
from app.modules.agent.schemas import (
    ChatOut,
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


async def chat(
    session: AsyncSession,
    couple: Couple,
    user: User,
    conversation_id: int,
    message: str,
    history: list[ChatTurn],
) -> ChatOut:
    """进行一轮对话。"""
    conversation = await _get_owned(session, couple, user, conversation_id)

    consent = await persona_repo.get_consent(
        session, couple.id, conversation.target_id
    )
    if consent is None or not consent.authorized:
        raise AppError(
            "对方还没有授权把 TA 的数据用于模拟", code=14001, status_code=403
        )

    target = await session.get(User, conversation.target_id)
    nickname = target.nickname if target is not None else "TA"

    fidelity_row = await persona_repo.get_settings(session, couple.id, user.id)
    fidelity = fidelity_row.fidelity if fidelity_row else "faithful"

    profile = await repo.get_profile(session, couple.id, conversation.target_id)

    fragments = await retrieval.collect_context(
        session, couple.id, conversation.target_id, query_text=message
    )
    context = "\n".join(fragments)

    system = _system_prompt(nickname, fidelity, profile, context)
    history_messages = await _load_history(
        session, conversation, history
    )

    reply = await ai_client.complete_chat(
        [{"role": "system", "content": system}]
        + history_messages
        + [{"role": "user", "content": message}]
    )

    if conversation.persist:
        await repo.add_message(
            session, conversation_id=conversation.id, role="user", content=message
        )
        await repo.add_message(
            session, conversation_id=conversation.id, role="assistant", content=reply
        )
        # 有新消息就顺延过期时间
        conversation.expires_at = datetime.now(UTC) + timedelta(
            days=settings.AGENT_RETENTION_DAYS
        )
        await session.commit()

    return ChatOut(
        conversation_id=conversation.id, reply=reply, disclaimer=DISCLAIMER
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
    limit = settings.AGENT_MAX_HISTORY_TURNS * 2

    if not conversation.persist:
        turns = request_history[-limit:]
        return [{"role": t.role, "content": t.content} for t in turns]

    rows = await repo.list_messages(session, conversation.id, limit)
    return [{"role": row.role, "content": row.content} for row in reversed(rows)]


def _system_prompt(
    nickname: str,
    fidelity: str,
    profile: PersonaProfile | None,
    context: str,
) -> str:
    """组装人格 prompt。

    顺序：身份 -> 规则 -> 风格画像 -> 典型发言 -> 检索上下文 -> 边界
    """
    parts = [
        f"你正在扮演 {nickname}，用 TA 的方式和用户聊天。",
        IDEALIZED_RULES if fidelity == "idealized" else FAITHFUL_RULES,
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
        "只使用以上记录里的信息和口吻。不确定就说不确定，不要编造。"
        "不要替 TA 做承诺。"
    )
    return "\n\n".join(parts)
