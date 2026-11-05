"""清单模块的请求 / 响应结构。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TodoCreate(BaseModel):
    """新建清单项。默认是共同清单。"""

    type: Literal["shared", "personal"] = "shared"
    category: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)


class TodoUpdate(BaseModel):
    """部分更新。字段都可选，只改传了的。"""

    category: str | None = Field(default=None, min_length=1, max_length=50)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    status: Literal["pending", "completed", "cancelled"] | None = None


class TodoOut(BaseModel):
    """清单项。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    category: str
    title: str
    description: str | None
    status: str
    creator_id: int
    completed_at: datetime | None
    created_at: datetime


class MemoryCard(BaseModel):
    """完成时生成的小纪念卡片。

    目前只是文案，前端可以拿它渲染成可分享的图。
    """

    title: str
    completed_at: datetime
    note: str


class TodoCompleteOut(BaseModel):
    """完成接口的返回：更新后的清单项 + 纪念卡片。"""

    todo: TodoOut
    card: MemoryCard
