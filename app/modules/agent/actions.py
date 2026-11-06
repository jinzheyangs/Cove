"""Agent 写操作的确认流程。

模型只能创建 pending 动作，不能直接写。
真正的执行由用户点击确认后触发，保证是本人授权。

当前支持：
- create_todo：添加到共同清单
"""

import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.agent.models import AgentAction, AgentConversation
from app.modules.audit import service as audit_service
from app.modules.couples.models import Couple
from app.modules.todos import service as todo_service
from app.modules.todos.schemas import TodoCreate
from app.modules.users.models import User

# 待确认动作的有效期
ACTION_TTL = timedelta(minutes=10)
EXPIRES_IN_SECONDS = int(ACTION_TTL.total_seconds())


async def create_pending(
    session: AsyncSession,
    conversation: AgentConversation,
    user: User,
    action_type: str,
    payload: dict,
) -> AgentAction:
    """创建一条待确认动作。立即提交，保证卡片发出去后动作已存在。"""
    action = AgentAction(
        conversation_id=conversation.id,
        user_id=user.id,
        type=action_type,
        payload=json.dumps(payload, ensure_ascii=False),
        expires_at=datetime.now(UTC) + ACTION_TTL,
    )
    session.add(action)
    await session.commit()
    await session.refresh(action)
    return action


async def get_action(session: AsyncSession, action_id: int) -> AgentAction | None:
    return await session.get(AgentAction, action_id)


async def _get_owned(
    session: AsyncSession, couple: Couple, user: User, action_id: int
) -> AgentAction:
    """取出动作并校验归属：属于当前用户、当前关系。"""
    action = await session.get(AgentAction, action_id)
    if action is None or action.user_id != user.id:
        raise AppError("操作不存在", code=17011, status_code=404)

    conversation = await session.get(AgentConversation, action.conversation_id)
    if conversation is None or conversation.couple_id != couple.id:
        raise AppError("操作不存在", code=17011, status_code=404)
    return action


async def confirm(
    session: AsyncSession, couple: Couple, user: User, action_id: int
) -> tuple[AgentAction, dict]:
    """确认并执行动作。

    幂等：重复确认不会重复写入，直接返回第一次的结果。
    """
    action = await _get_owned(session, couple, user, action_id)

    if action.status == "confirmed":
        return action, json.loads(action.result or "{}")

    if action.status != "pending":
        raise AppError("这个操作已经不能确认了", code=17012, status_code=409)

    if action.expires_at <= datetime.now(UTC):
        action.status = "expired"
        await session.commit()
        raise AppError("确认已过期，请重新发起", code=17010, status_code=410)

    payload = json.loads(action.payload or "{}")
    result = await _execute(session, couple, user, action, payload)

    action.status = "confirmed"
    action.decided_at = datetime.now(UTC)
    action.result = json.dumps(result, ensure_ascii=False)
    await audit_service.record(
        session,
        user_id=user.id,
        couple_id=couple.id,
        action=f"agent.{action.type}.confirm",
        target_type="agent_action",
        target_id=action.id,
    )
    await session.commit()
    await session.refresh(action)
    return action, result


async def cancel(
    session: AsyncSession, couple: Couple, user: User, action_id: int
) -> AgentAction:
    """取消动作，不执行任何写入。"""
    action = await _get_owned(session, couple, user, action_id)

    if action.status != "pending":
        return action

    action.status = "cancelled"
    action.decided_at = datetime.now(UTC)
    await audit_service.record(
        session,
        user_id=user.id,
        couple_id=couple.id,
        action=f"agent.{action.type}.cancel",
        target_type="agent_action",
        target_id=action.id,
    )
    await session.commit()
    await session.refresh(action)
    return action


async def delete_for_conversation(
    session: AsyncSession, conversation_id: int
) -> None:
    """删除会话时一并清理它的待确认动作。"""
    await session.execute(
        delete(AgentAction).where(AgentAction.conversation_id == conversation_id)
    )
    await session.flush()


async def _execute(
    session: AsyncSession,
    couple: Couple,
    user: User,
    action: AgentAction,
    payload: dict,
) -> dict:
    """按动作类型执行真正的写入。

    新增类型时在这里加分支，并确保参数经过校验。
    """
    if action.type == "create_todo":
        todo = await todo_service.create(
            session,
            couple,
            user,
            TodoCreate(
                title=payload["title"],
                category=payload.get("category") or "想实现的约定",
                description=payload.get("description"),
            ),
        )
        return {"todo_id": todo.id}

    raise AppError("不支持的操作类型", code=17013, status_code=400)
