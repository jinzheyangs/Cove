"""情侣模块的请求 / 响应结构。"""

from datetime import date as date_type
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.time import today


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


class PartnerOut(BaseModel):
    """关系里的另一半。日记页要按 author_id 分「我 / TA」，还得把昵称显示出来。"""

    id: int
    nickname: str
    avatar_url: str | None = None


class CoupleOut(BaseModel):
    """关系信息。不暴露 status/unbound_at，活跃关系由 /couples/me 保证。

    start_date 为空时，客户端按 bind_at 的日期兜底显示。
    partner 是当前请求者的另一半，只在 /couples/me 里填。
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    user1_id: int
    user2_id: int
    bind_at: datetime
    start_date: date_type | None = None
    # 发起这段关系的人（邀请码的发起者）。前端据此只让发起人去填「在一起那天」。
    created_by: int | None = None
    partner: PartnerOut | None = None


class CoupleUpdate(BaseModel):
    """更新关系资料。目前只开放「在一起」的起始日。

    传 null 表示清空，显示时会退回 bind_at 的日期。
    """

    start_date: date_type | None = None

    @field_validator("start_date")
    @classmethod
    def _start_date_not_future(cls, value: date_type | None) -> date_type | None:
        if value is not None and value > today():
            raise ValueError("在一起的日子不能是未来")
        return value


class UsStatsOut(BaseModel):
    """解绑前给两个人看的那张「你们攒下了什么」。

    只读、只统计，不参与任何业务判断。
    """

    days_together: int
    since: date_type | None = None
    diaries: int = 0
    secrets: int = 0
    todos_pending: int = 0
    todos_done: int = 0
    bills: int = 0
    anniversaries: int = 0
    coins: int = 0
    partner_nickname: str | None = None

