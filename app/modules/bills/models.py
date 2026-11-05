from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.types import EncryptedText


class Bill(Base):
    """恋爱账本。

    type 非 money 时 amount 为空——这类付出不量化，避免变成对比排行。
    """

    __tablename__ = "bills"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("couples.id"))
    payer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    category: Mapped[str] = mapped_column(String(50))
    type: Mapped[str] = mapped_column(String(20), default="money", server_default="money")
    scope: Mapped[str] = mapped_column(String(20), default="shared", server_default="shared")
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    remark: Mapped[str | None] = mapped_column(EncryptedText)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "type IN ('money', 'time', 'energy', 'emotion')", name="ck_bills_type"
        ),
        CheckConstraint("scope IN ('shared', 'personal')", name="ck_bills_scope"),
        CheckConstraint("amount IS NULL OR amount >= 0", name="ck_bills_amount"),
        Index("ix_bills_couple_created", "couple_id", "created_at"),
    )
