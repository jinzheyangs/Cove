from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApplyCreate(BaseModel):
    amount: int = Field(gt=0, le=100_000)
    reason: str = Field(min_length=1, max_length=500)


class ApproveRequest(BaseModel):
    amount: int | None = Field(default=None, gt=0, le=100_000)
    remark: str | None = Field(default=None, max_length=200)


class RejectRequest(BaseModel):
    remark: str | None = Field(default=None, max_length=200)


class ApplyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    applicant_id: int
    amount: int
    reason: str
    status: str
    approved_amount: int | None
    decision_remark: str | None
    created_at: datetime
    decided_at: datetime | None
