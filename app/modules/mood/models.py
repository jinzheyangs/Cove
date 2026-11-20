"""每日心情表结构。

设计目标：双方各自记录今天的心情，互相可见。
- 每人每天最多一条，唯一约束保证，重复提交是修改
- 心情类型与等级分开存，一句话加密存储
"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.types import EncryptedText

# 合法心情类型，schema 与 check 约束共用同一份定义
MOOD_VALUES = ("awesome", "happy", "calm", "tired", "low")


class MoodRecord(Base):
    """某人某天的一条心情。"""

    __tablename__ = "mood_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("couples.id"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    # 按北京时间切天
    day: Mapped[date] = mapped_column(Date)
    # 心情类型代码，对应前端的自绘图标；
    # 可以为空：只写了一句话、没标情绪的也算一条记录
    mood: Mapped[str | None] = mapped_column(String(20))
    # 心情等级 1-5，对应前端圆点；没选心情时用中间值 3 兜底
    level: Mapped[int] = mapped_column(SmallInteger)
    # 一句话，可空，加密存储
    note: Mapped[str | None] = mapped_column(EncryptedText)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("level BETWEEN 1 AND 5", name="ck_mood_level"),
        CheckConstraint("mood IN ('awesome','happy','calm','tired','low')", name="ck_mood_type"),
        # 每人每天只有一条
        UniqueConstraint("couple_id", "user_id", "day", name="uq_mood_couple_user_day"),
        Index("ix_mood_records_day", "couple_id", "day"),
    )
