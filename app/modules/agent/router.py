"""AI 对话服务的 HTTP 接口。

会话默认保存在服务端，30 天过期；
也可以创建 persist=false 的会话，服务端不存消息。
"""

import json
from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.deps import CurrentUser, SessionDep
from app.core.errors import AppError
from app.core.schemas import Envelope
from app.modules.agent import import_service, importers, service
from app.modules.agent.schemas import (
    ChatImportOut,
    ChatIn,
    ConversationCreate,
    ConversationDetailOut,
    ConversationOut,
)
from app.modules.couples.deps import CurrentCouple

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/imports", response_model=Envelope[ChatImportOut])
async def import_chat_log(
    couple: CurrentCouple,
    user: CurrentUser,
    session: SessionDep,
    file: Annotated[UploadFile, File(description="JSONL 或 JSON 聊天记录")],  #；聊天记录
    format: Annotated[str | None, Form()] = None,
    owner_name: Annotated[str | None, Form()] = None,       #我的昵称
    partner_name: Annotated[str | None, Form()] = None,     #对方昵称
) -> Envelope[ChatImportOut]:
    """导入聊天记录。

    双方都授权后才能导入。原始文件只在内存里解析，不落盘。
    导入后画像和向量索引在后台完成。
    """
    data = await file.read(settings.CHAT_IMPORT_MAX_BYTES + 1)
    if len(data) > settings.CHAT_IMPORT_MAX_BYTES:
        raise AppError("文件太大", code=17004, status_code=413)

    fmt = (format or importers.detect_format(file.filename or "")).lower()
    if fmt not in ("jsonl", "json"):
        raise AppError("只支持 jsonl / json 格式", code=17005, status_code=400)

    row = await import_service.import_chat_log(
        session,
        couple,
        user,
        filename=file.filename or "chat.jsonl",
        fmt=fmt,
        raw=data,
        owner_name=owner_name,
        partner_name=partner_name,
    )
    return Envelope(data=ChatImportOut.model_validate(row))


@router.get("/imports", response_model=Envelope[list[ChatImportOut]])
async def list_imports(
    couple: CurrentCouple, session: SessionDep
) -> Envelope[list[ChatImportOut]]:
    """查看历史导入记录和状态。"""
    rows = await import_service.list_imports(session, couple)
    return Envelope(data=[ChatImportOut.model_validate(row) for row in rows])


@router.get("/imports/{import_id}", response_model=Envelope[ChatImportOut])
async def get_import(
    import_id: int, couple: CurrentCouple, session: SessionDep
) -> Envelope[ChatImportOut]:
    """查看单次导入的状态和计数。"""
    row = await import_service.get_import(session, couple, import_id)
    return Envelope(data=ChatImportOut.model_validate(row))


@router.delete("/imports/{import_id}", response_model=Envelope[None])
async def delete_import(
    import_id: int, couple: CurrentCouple, session: SessionDep
) -> Envelope[None]:
    """删除一次导入：消息、向量、画像一起清理。"""
    await import_service.delete_import(session, couple, import_id)
    return Envelope()


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


@router.get("/conversations", response_model=Envelope[list[ConversationOut]])
async def list_conversations(
    user: CurrentUser, session: SessionDep
) -> Envelope[list[ConversationOut]]:
    """我发起过的会话，按最近活动排序。"""
    conversations = await service.list_conversations(session, user)
    return Envelope(
        data=[ConversationOut.model_validate(c) for c in conversations]
    )


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


@router.delete("/conversations/{conversation_id}", response_model=Envelope[None])
async def delete_conversation(
    conversation_id: int,
    user: CurrentUser,
    couple: CurrentCouple,
    session: SessionDep,
) -> Envelope[None]:
    """删除会话及其全部消息。"""
    await service.delete_conversation(session, couple, user, conversation_id)
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
    await service.validate_for_chat(session, couple, user, conversation_id)
    couple_id = couple.id
    user_id = user.id

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
                yield _sse("done", {"conversation_id": conversation_id})
            except AppError as exc:
                yield _sse("error", {"code": exc.code, "message": exc.message})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
