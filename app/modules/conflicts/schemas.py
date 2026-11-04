from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class ReviewCreate(BaseModel):
    want_to_be_understood: str = Field(min_length=1, max_length=1000)
    heard_partner_need: str = Field(min_length=1, max_length=1000)


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    content: str
    flagged: bool
    created_at: datetime


class MessageSentOut(BaseModel):
    message: MessageOut
    # 命中伤害词时给一句温和提示，不阻断发送
    gentle_prompt: str | None = None


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    want_to_be_understood: str
    heard_partner_need: str
    created_at: datetime


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    started_at: datetime
    ended_at: datetime | None


class SessionDetailOut(SessionOut):
    messages: list[MessageOut]
    reviews: list[ReviewOut]
