from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InviteOut(BaseModel):
    code: str
    expires_at: datetime


class BindRequest(BaseModel):
    code: str = Field(min_length=4, max_length=12)


class CoupleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user1_id: int
    user2_id: int
    bind_at: datetime
