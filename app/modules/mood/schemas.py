"""每日心情的请求 / 响应结构。"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

MoodType = Literal["awesome", "happy", "calm", "tired", "low"]


class MoodOut(BaseModel):
    """单条心情。

    mood 可以为空：光写一句话、不标情绪也是合法的一天。
    """

    id: int
    day: date
    user_id: int
    mood: MoodType | None = None
    level: int
    note: str | None


class MoodPairOut(BaseModel):
    """今日双方心情：自己的一条 + 对方的一条。"""

    day: date
    mine: MoodOut | None
    partner: MoodOut | None


class MoodCreate(BaseModel):
    """提交或修改今天的心情。

    两种写法都收：
    - 选了心情（可以顺手带一句备注）
    - 只写字、不选心情 —— 这时 mood 留空，level 用中间值兜底

    只要求「心情」和「备注」至少给一个，不能整条空白。
    """

    mood: MoodType | None = None
    level: int = Field(default=3, ge=1, le=5)
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _at_least_one(self) -> "MoodCreate":
        if self.mood is None and not (self.note or "").strip():
            raise ValueError("心情和备注至少要写一个")
        return self
