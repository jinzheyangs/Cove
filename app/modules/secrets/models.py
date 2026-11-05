from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.types import EncryptedText


class Secret(Base):
    __tablename__ = "secrets"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("couples.id"))
    author_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(EncryptedText)
    level: Mapped[str] = mapped_column(String(20), default="normal", server_default="normal")
    cost_coins: Mapped[int] = mapped_column(BigInteger)
    is_burn_after_read: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    status: Mapped[str] = mapped_column(String(20), default="active", server_default="active")
    viewed_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("level IN ('normal', 'deep')", name="ck_secrets_level"),
        CheckConstraint(
            "status IN ('active', 'burned', 'destroyed')", name="ck_secrets_status"
        ),
        CheckConstraint("cost_coins > 0", name="ck_secrets_cost_positive"),
        Index("ix_secrets_couple_status", "couple_id", "status"),
        Index("ix_secrets_author", "author_id"),
    )
