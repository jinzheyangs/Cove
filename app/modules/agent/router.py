"""AI 对话服务的 HTTP 接口。

会话默认保存在服务端，30 天过期；
也可以创建 persist=false 的会话，服务端不存消息。
"""

from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile

from app.core.config import settings
from app.core.deps import CurrentUser, SessionDep
from app.core.errors import AppError
from app.core.schemas import Envelope
from app.modules.agent import import_service, importers, service
from app.modules.agent.schemas import (
    ChatImportOut,
    ChatIn,
    ChatOut,
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
    file: Annotated[UploadFile, File(description="JSONL 或 JSON 聊天记录")],
    format: Annotated[str | None, Form()] = None,
    owner_name: Annotated[str | None, Form()] = None,
    partner_name: Annotated[str | None, Form()] = None,
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


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=Envelope[ChatOut],
)
async def chat(
    conversation_id: int,
    body: ChatIn,
    user: CurrentUser,
    couple: CurrentCouple,
    session: SessionDep,
) -> Envelope[ChatOut]:
    """发送一条消息，返回分身的回复。

    需要对方已授权。会话设置为不保存时，客户端需要自带 history。
    """
    result = await service.chat(
        session, couple, user, conversation_id, body.message, body.history
    )
    return Envelope(data=result)
