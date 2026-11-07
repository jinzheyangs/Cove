"""纪念日模块的请求 / 响应结构。"""

from datetime import date as date_type
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AnniversaryCreate(BaseModel):
    """自定义纪念日。日期可以是将来的，也可以是过去的。"""

    title: str = Field(min_length=1, max_length=50)
    date: date_type
    repeat_yearly: bool = True
    idempotency_key: str | None = Field(default=None, max_length=64)

    @field_validator("title")
    @classmethod
    def _strip_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("标题不能为空")
        return value


class AnniversaryUpdate(BaseModel):
    """部分更新。只传要改的字段。"""

    title: str | None = Field(default=None, min_length=1, max_length=50)
    date: date_type | None = None
    repeat_yearly: bool | None = None

    @field_validator("title")
    @classmethod
    def _strip_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("标题不能为空")
        return value


class AnniversaryOut(BaseModel):
    """统一后的倒计时条目。

    source 区分来源：
    - relationship：在一起，来自 couples.bind_at
    - birthday：双方生日，来自 users.birthday
    - custom：用户自定义，来自 anniversaries 表

    date 是原始日期，next_date 是下一次发生的日期。
    一次性事件过期后 days_left 为负数、passed=true。
    """

    id: int | None = None
    source: Literal["relationship", "birthday", "custom"]
    title: str
    date: date_type
    next_date: date_type
    days_left: int
    # 到下一次时是第几周年 / 第几岁；一次性事件为 None
    years: int | None = None
    is_today: bool
    passed: bool
    repeat_yearly: bool
    owner_id: int | None = None
    # 关系纪念日和生日由专门接口维护，这里只允许改自定义纪念日
    editable: bool = False
