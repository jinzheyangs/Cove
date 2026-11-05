"""金币模块的请求 / 响应结构。"""

from datetime import datetime

from pydantic import BaseModel, Field

# 单次赠与的绝对上限，防止误操作或刷接口
MAX_GIFT = 100_000


class GiftRequest(BaseModel):
    """赠与金币。

    idempotency_key 建议由客户端生成（如 UUID），
    网络重试或用户连点时会复用同一个值，服务端只生效一次。
    不传的话服务端会生成随机值，此时重复提交无法去重。
    """

    amount: int = Field(gt=0, le=MAX_GIFT)
    remark: str | None = Field(default=None, max_length=200)
    # 客户端应传一个稳定值（如 UUID），重复提交时只生效一次
    idempotency_key: str | None = Field(default=None, max_length=64)


class BalanceOut(BaseModel):
    """余额。只返回数字，不带任何明细。"""

    balance: int


class TransactionItem(BaseModel):
    """流水条目。

    direction 是服务端根据当前用户算好的：
    - in：这笔钱进了我的账户
    - out：这笔钱从我的账户出去，或者是我发起的赠与
    """

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
