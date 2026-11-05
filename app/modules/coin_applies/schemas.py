"""金币申请的请求 / 响应结构。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApplyCreate(BaseModel):
    """发起申请。reason 必填，避免出现没有上下文的高额申请。"""

    amount: int = Field(gt=0, le=100_000)
    reason: str = Field(min_length=1, max_length=500)


class ApproveRequest(BaseModel):
    """审批通过。

    amount 不传则按申请金额发放；
    传了就以传入值为准（可以调高或调低）。
    """

    amount: int | None = Field(default=None, gt=0, le=100_000)
    remark: str | None = Field(default=None, max_length=200)


class RejectRequest(BaseModel):
    """拒绝。remark 会展示给申请人，建议写清楚原因。"""

    remark: str | None = Field(default=None, max_length=200)


class ApplyOut(BaseModel):
    """申请详情。同时包含申请金额和实际通过金额。"""

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
