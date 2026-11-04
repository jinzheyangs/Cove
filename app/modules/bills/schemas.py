from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BillCreate(BaseModel):
    amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    category: str = Field(min_length=1, max_length=50)
    type: Literal["money", "time", "energy", "emotion"] = "money"
    scope: Literal["shared", "personal"] = "shared"
    is_private: bool = False
    remark: str | None = Field(default=None, max_length=500)


class BillOut(BaseModel):
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
    category: str
    total: Decimal


class BillStats(BaseModel):
    """只给共同视角的汇总，不提供「谁花得多」的对比。"""

    count: int
    money_total: Decimal
    shared_total: Decimal
    personal_total: Decimal
    by_category: list[CategoryStat]
    non_money_counts: dict[str, int]
