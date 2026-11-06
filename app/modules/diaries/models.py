"""恋爱日记表结构。

两种模式：
- shared：两个人共同编辑同一篇
- personal：各自视角。同一件事的两篇用 event_id 关联，
  查询时传同一个 event_id 就能拿到两种视角。

标题和正文加密存储；情绪标签、地点、图片按普通字段存。
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.types import EncryptedText


class Diary(Base):
    """一篇日记。

    权限规则在 service 层：
    - personal：只有作者能改/删
    - shared：双方都能改/删
    """

    __tablename__ = "diaries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("couples.id"))
    # 「各自视角」的关联键。同一件事的两个人传同一个值
    event_id: Mapped[str | None] = mapped_column(String(36), index=True)
    # shared / personal
    mode: Mapped[str] = mapped_column(String(20))
    title: Mapped[str | None] = mapped_column(EncryptedText)
    content: Mapped[str] = mapped_column(EncryptedText)
    # 情绪标签，用于时光轴和年度回顾
    mood_tags: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    location: Mapped[str | None] = mapped_column(String(200))
    # 图片 URL 列表，文件本身在对象存储
    images: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    # personal 模式下必填；shared 模式下是最后编辑人
    author_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    # 客户端幂等键：同一个 key 重复提交只创建一条
    idempotency_key: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("mode IN ('shared', 'personal')", name="ck_diaries_mode"),
        # 列表按关系 + 时间排序
        Index("ix_diaries_couple_created", "couple_id", "created_at"),
        # 幂等键在关系内唯一；NULL 不参与约束
        Index(
            "uq_diaries_idempotency",
            "couple_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )
