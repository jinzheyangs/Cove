"""账本模块的请求 / 响应结构。"""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BillCreate(BaseModel):
    """新增 / 更新一条账目。

    金额规则在 service 层强制：
    - type=money 时必须填 amount
    - 其他类型不允许填 amount（避免把陪伴、情绪劳动量化成分数）
    """

    amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    category: str = Field(min_length=1, max_length=50)
    type: Literal["money", "time", "energy", "emotion"] = "money"
    scope: Literal["shared", "personal"] = "shared"
    is_private: bool = False
    remark: str | None = Field(default=None, max_length=500)
    # 客户端生成的稳定值，重复提交只创建一条
    idempotency_key: str | None = Field(default=None, max_length=64)


class BillOut(BaseModel):
    """账目详情。remark 返回时已解密。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    payer_id: int
    amount: Decimal | None
    category: str
    type: str
    scope: str
    is_private: bool
    remark: str | None
    created_at: datetime


class CategoryStat(BaseModel):
    """单个分类的金额合计。"""

    category: str
    total: Decimal


class BillStats(BaseModel):
    """统计结果。

    刻意**没有**「每人花了多少」字段：
    那会把记录变成算账工具，和产品调性冲突。
    """

    count: int
    money_total: Decimal
    shared_total: Decimal
    personal_total: Decimal
    by_category: list[CategoryStat]
    # 非金钱付出只给次数，不折算成金额
    non_money_counts: dict[str, int]
