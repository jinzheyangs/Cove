from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InviteOut(BaseModel):
    code: str
    expires_at: datetime


class BindRequest(BaseModel):
    code: str = Field(min_length=4, max_length=12)


class UnbindRequest(BaseModel):
    # 必须显式确认，避免误触
    confirm: bool = False
    reason: str | None = Field(default=None, max_length=200)


class CoupleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user1_id: int
    user2_id: int
    bind_at: datetime
