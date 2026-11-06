"""AI 对话服务的 HTTP 接口。

会话默认保存在服务端，30 天过期；
也可以创建 persist=false 的会话，服务端不存消息。
"""

from fastapi import APIRouter

from app.core.deps import CurrentUser, SessionDep
from app.core.schemas import Envelope
from app.modules.agent import service
from app.modules.agent.schemas import (
    ChatIn,
    ChatOut,
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
