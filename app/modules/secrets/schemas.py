"""秘密模块的请求 / 响应结构。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# 不填价格时的默认值：深度秘密更贵，形成“想让你认真读”的信号
DEFAULT_COST = {"normal": 10, "deep": 30}


class SecretCreate(BaseModel):
    """发布秘密。

    cost_coins 不传时按 level 取默认值。
    作者可以自己定价：定低是“希望你快读”，定高是“这件事对我很重要”。
    """

    content: str = Field(min_length=1, max_length=5000)
    level: Literal["normal", "deep"] = "normal"
    cost_coins: int | None = Field(default=None, ge=1, le=1000)
    is_burn_after_read: bool = False


class SecretListItem(BaseModel):
    """列表项。**刻意不包含 content**，内容只能通过 unlock 获取。"""

    id: int
    level: str
    cost_coins: int
    is_burn_after_read: bool
    status: str
    authored_by_me: bool
    viewed: bool
    created_at: datetime


class SecretDetail(BaseModel):
    """摘取成功后返回的内容。"""

    id: int
    content: str
    level: str
    cost_coins: int
    is_burn_after_read: bool
    status: str
    created_at: datetime
