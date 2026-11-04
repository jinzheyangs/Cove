from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class DailyAnswer(Base):
    __tablename__ = "daily_answers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("couples.id"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    day: Mapped[date] = mapped_column(Date)
    question: Mapped[str] = mapped_column(String(200))
    answer: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("couple_id", "user_id", "day", name="uq_daily_couple_user_day"),
        Index("ix_daily_answers_day", "couple_id", "day"),
    )
