"""每日一问的表结构。

设计目标是“每天有一个打开 App 的理由”，所以刻意做得极轻：
- 没有 AI 调用
- 题库放在库里（daily_questions），改题直接改库，不用改代码重启
- 每人每天最多一条，唯一约束保证
"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.types import EncryptedText


class DailyQuestion(Base):
    """题库。一行一道题。

    想加题就往这张表里插一行；想下架某道题把 is_active 置 false，
    不用改代码、不用重启。sort_order 只决定取题时要遍历的顺序。
    """

    __tablename__ = "daily_questions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(String(200), unique=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (Index("ix_daily_questions_order", "is_active", "sort_order"),)


class DailyAnswer(Base):
    """某人某天对某个问题的回答。"""

    __tablename__ = "daily_answers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("couples.id"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    # 按北京时间切天，而不是 UTC
    day: Mapped[date] = mapped_column(Date)
    # 问题文案冗余存一份：题库以后改版，历史记录也不会错位
    question: Mapped[str] = mapped_column(String(200))
    answer: Mapped[str] = mapped_column(EncryptedText)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        # 每人每天只有一条，重复提交是修改
        UniqueConstraint("couple_id", "user_id", "day", name="uq_daily_couple_user_day"),
        Index("ix_daily_answers_day", "couple_id", "day"),
    )
