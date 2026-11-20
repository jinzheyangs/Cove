"""AI 对话服务的 HTTP 接口。

会话默认保存在服务端，30 天过期；
也可以创建 persist=false 的会话，服务端不存消息。
"""

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core.db import SessionLocal
from app.core.deps import CurrentUser, SessionDep
from app.core.errors import AppError
from app.core.schemas import Envelope
from app.modules.agent import actions, service
from app.modules.agent.schemas import (
    ActionOut,
    ChatIn,
    ConversationCreate,
    ConversationDetailOut,
    ConversationOut,
)
from app.modules.couples.deps import CurrentCouple

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/conversations", response_model=Envelope[ConversationOut])
async def create_conversation(
    body: ConversationCreate,
    user: CurrentUser,
    couple: CurrentCouple,
    session: SessionDep,
) -> Envelope[ConversationOut]:
    """新建会话，被模拟对象固定为伴侣。"""
    conversation = await service.create_conversation(
        session, couple, user, body.title, body.persist
    )
    return Envelope(data=ConversationOut.model_validate(conversation))


@router.get(
    "/conversations/{conversation_id}",
    response_model=Envelope[ConversationDetailOut],
)
async def get_detail(
    conversation_id: int,
    user: CurrentUser,
    couple: CurrentCouple,
    session: SessionDep,
) -> Envelope[ConversationDetailOut]:
    """会话详情，包含消息记录。"""
    detail = await service.get_detail(session, couple, user, conversation_id)
    return Envelope(data=detail)


@router.post("/conversations/{conversation_id}/memorize", response_model=Envelope[None])
async def memorize_conversation(
    conversation_id: int,
    user: CurrentUser,
    couple: CurrentCouple,
    session: SessionDep,
) -> Envelope[None]:
    """把这次对话切块存成长期记忆。

    前端在离开「模拟 Ta」页面时调用；重复调用幂等。
    """
    await service.memorize_conversation(session, couple, user, conversation_id)
    return Envelope()


def _sse(event: str, data: dict) -> str:
    """拼一条 SSE 事件。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/conversations/{conversation_id}/messages/stream")
async def chat_stream(
    conversation_id: int,
    body: ChatIn,
    user: CurrentUser,
    couple: CurrentCouple,
    session: SessionDep,
) -> StreamingResponse:
    """流式对话（SSE），工具调用也在流里。

    事件类型：
    - delta: 文本片段
    - tool:  工具状态（running / done），只含名称和可读标签
    - done:  本轮结束
    - error: 出错，附带业务错误码

    先在普通请求里完成归属和授权校验，错误能以正常 HTTP 状态返回；
    校验通过后再切换成事件流。
    """
    await service.validate_for_chat(session, couple, user, conversation_id)     #对话检验
    couple_id = couple.id       #情侣id
    user_id = user.id           #发起id

    async def event_stream():
        # 流式响应会超出请求依赖的生命周期，所以自己开一个会话
        async with SessionLocal() as stream_session:
            try:
                async for kind, payload in service.stream_reply(
                    stream_session,
                    couple_id,
                    user_id,
                    conversation_id,
                    body.message,
                    body.history,
                ):
                    if kind == "delta":
                        yield _sse("delta", {"delta": payload})
                    elif kind == "tool":
                        yield _sse("tool", payload)
                    elif kind == "confirm":
                        yield _sse("confirm", payload)
                yield _sse("done", {"conversation_id": conversation_id})
            except AppError as exc:
                yield _sse("error", {"code": exc.code, "message": exc.message})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/actions/{action_id}/confirm", response_model=Envelope[ActionOut])
async def confirm_action(
    action_id: int,
    user: CurrentUser,
    couple: CurrentCouple,
    session: SessionDep,
) -> Envelope[ActionOut]:
    """确认 Agent 提议的写操作。

    只有发起动作的人能确认；重复确认是幂等的，不会重复写入。
    """
    action, result = await actions.confirm(session, couple, user, action_id)
    return Envelope(
        data=ActionOut(
            action_id=action.id,
            type=action.type,
            status=action.status,
            result=result,
        )
    )


@router.post("/actions/{action_id}/cancel", response_model=Envelope[ActionOut])
async def cancel_action(
    action_id: int,
    user: CurrentUser,
    couple: CurrentCouple,
    session: SessionDep,
) -> Envelope[ActionOut]:
    """取消 Agent 提议的写操作。不会产生任何写入。"""
    action = await actions.cancel(session, couple, user, action_id)
    return Envelope(
        data=ActionOut(
            action_id=action.id,
            type=action.type,
            status=action.status,
        )
    )
