"""纪念日表结构。

- 「在一起」不落表，直接由 couples.bind_at 计算
- 双方生日存在 users.birthday
- 这里只存用户自定义的纪念日

date 存的是原始日期（第一次发生的那天）。
repeat_yearly=true 时每次读取计算下一次出现日期；
false 表示一次性事件，过期后仍保留，由前端决定是否隐藏。
"""

from datetime import date as date_type
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Anniversary(Base):
    __tablename__ = "anniversaries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("couples.id"))
    # 创建者只用于审计；纪念日本身是双方共享的
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(50))
    # 原始日期：比如在一起的那天、第一次旅行的那天
    date: Mapped[date_type] = mapped_column(Date)
    repeat_yearly: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    # 客户端幂等键：同一个 key 重复提交只创建一条
    idempotency_key: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_anniversaries_couple_date", "couple_id", "date"),
        Index(
            "uq_anniversaries_idempotency",
            "couple_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )
