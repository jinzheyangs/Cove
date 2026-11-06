"""AI 对话服务的请求 / 响应结构。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    """新建会话。

    persist=False 时服务端不保存消息，客户端每次请求要自己带 history。
    """

    title: str | None = Field(default=None, max_length=100)
    persist: bool = True


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    target_id: int
    title: str | None
    persist: bool
    created_at: datetime
    updated_at: datetime
    expires_at: datetime


class ChatTurn(BaseModel):
    """客户端自带的历史消息（仅在 persist=False 时需要）。"""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatIn(BaseModel):
    """一轮对话请求。

    history 只在会话设置为不保存时使用；
    服务端保存的会话会自动读取历史，不需要重复传。
    """

    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=40)


class ChatOut(BaseModel):
    conversation_id: int
    reply: str
    disclaimer: str


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: str
    content: str
    created_at: datetime


class ConversationDetailOut(ConversationOut):
    messages: list[MessageOut]


class ChatImportOut(BaseModel):
    """一次聊天记录导入的状态。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    format: str
    status: str
    total_messages: int
    imported_messages: int
    indexed_windows: int
    skipped_messages: int
    error: str | None
    created_at: datetime
    finished_at: datetime | None
