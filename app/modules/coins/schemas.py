from datetime import datetime

from pydantic import BaseModel, Field

MAX_GIFT = 100_000


class GiftRequest(BaseModel):
    amount: int = Field(gt=0, le=MAX_GIFT)
    remark: str | None = Field(default=None, max_length=200)
    # 客户端应传一个稳定值（如 UUID），重复提交时只生效一次
    idempotency_key: str | None = Field(default=None, max_length=64)


class BalanceOut(BaseModel):
    balance: int


class TransactionItem(BaseModel):
    id: int
    type: str
    direction: str  # in = 收入，out = 支出
    amount: int
    from_user_id: int | None
    to_user_id: int | None
    ref_type: str | None
    ref_id: int | None
    remark: str | None
    created_at: datetime
