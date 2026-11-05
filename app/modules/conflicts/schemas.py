"""争吵模块的请求 / 响应结构。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MessageCreate(BaseModel):
    """发送一条消息。内容加密存储。"""

    content: str = Field(min_length=1, max_length=2000)


class ReviewCreate(BaseModel):
    """提交复盘。两个问题都必须回答，不接受空字符串。"""

    want_to_be_understood: str = Field(min_length=1, max_length=1000)
    heard_partner_need: str = Field(min_length=1, max_length=1000)


class MessageOut(BaseModel):
    """消息详情。flagged 表示命中了伤害词。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    content: str
    flagged: bool
    created_at: datetime


class MessageSentOut(BaseModel):
    """发送结果。

    gentle_prompt 只在命中伤害词时有值，
    前端应把它作为温和提示展示，而不是错误弹窗。
    """

    message: MessageOut
    # 命中伤害词时给一句温和提示，不阻断发送
    gentle_prompt: str | None = None


class ReviewOut(BaseModel):
    """一份复盘。"""

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    want_to_be_understood: str
    heard_partner_need: str
    created_at: datetime


class SessionOut(BaseModel):
    """会话状态。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    started_at: datetime
    ended_at: datetime | None


class SessionDetailOut(SessionOut):
    """会话详情：状态 + 全部消息 + 已提交的复盘。"""

    messages: list[MessageOut]
    reviews: list[ReviewOut]
