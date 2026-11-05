"""情侣模块的请求 / 响应结构。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InviteOut(BaseModel):
    """邀请码返回。客户端展示 code，并提示 24 小时内有效。"""

    code: str
    expires_at: datetime


class BindRequest(BaseModel):
    """用邀请码绑定。

    长度放宽到 4-12，容忍客户端传小写或带空格，
    service 里会统一 strip + upper。
    """

    code: str = Field(min_length=4, max_length=12)


class UnbindRequest(BaseModel):
    """解除绑定。

    confirm 必须显式为 true，避免误触。
    reason 只写进审计日志，不会展示给对方。
    """

    confirm: bool = False
    reason: str | None = Field(default=None, max_length=200)


class CoupleOut(BaseModel):
    """关系信息。不暴露 status/unbound_at，活跃关系由 /couples/me 保证。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user1_id: int
    user2_id: int
    bind_at: datetime
