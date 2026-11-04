from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
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


class ConflictSession(Base):
    __tablename__ = "conflict_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("couples.id"))
    status: Mapped[str] = mapped_column(
        String(20), default="ongoing", server_default="ongoing"
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "status IN ('ongoing', 'cooling', 'reviewing', 'closed')",
            name="ck_conflict_sessions_status",
        ),
        Index("ix_conflict_sessions_couple", "couple_id", "status"),
    )


class ConflictMessage(Base):
    __tablename__ = "conflict_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("conflict_sessions.id")
    )
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (Index("ix_conflict_messages_session", "session_id"),)


class ConflictReview(Base):
    __tablename__ = "conflict_reviews"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("conflict_sessions.id")
    )
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    want_to_be_understood: Mapped[str] = mapped_column(Text)
    heard_partner_need: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("session_id", "user_id", name="uq_conflict_reviews_session_user"),
    )
