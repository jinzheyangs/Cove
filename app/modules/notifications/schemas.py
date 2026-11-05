"""站内通知的响应结构。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    """一条通知。related_type/related_id 用于前端跳转。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    title: str
    content: str | None
    related_type: str | None
    related_id: int | None
    is_read: bool
    created_at: datetime


class UnreadCountOut(BaseModel):
    """未读数。前端可用来渲染红点。"""

    unread: int
