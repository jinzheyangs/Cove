from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# 不填价格时的默认值
DEFAULT_COST = {"normal": 10, "deep": 30}


class SecretCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    level: Literal["normal", "deep"] = "normal"
    cost_coins: int | None = Field(default=None, ge=1, le=1000)
    is_burn_after_read: bool = False


class SecretListItem(BaseModel):
    """列表里不返回内容。"""

    id: int
    level: str
    cost_coins: int
    is_burn_after_read: bool
    status: str
    authored_by_me: bool
    viewed: bool
    created_at: datetime


class SecretDetail(BaseModel):
    id: int
    content: str
    level: str
    cost_coins: int
    is_burn_after_read: bool
    status: str
    created_at: datetime
