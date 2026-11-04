from datetime import datetime

from sqlalchemy import (
    BigInteger,
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


class InquirySession(Base):
    __tablename__ = "inquiry_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("couples.id"))
    question: Mapped[str] = mapped_column(Text)
    ai_response: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20), default="collecting", server_default="collecting"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "status IN ('collecting', 'ai_processing', 'reviewing', 'closed')",
            name="ck_inquiry_sessions_status",
        ),
        Index("ix_inquiry_sessions_couple", "couple_id"),
    )


class InquiryInput(Base):
    """双方各自写下的真实想法。对外不暴露是谁写的。"""

    __tablename__ = "inquiry_inputs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("inquiry_sessions.id"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("session_id", "user_id", name="uq_inquiry_inputs_session_user"),
    )


class InquirySupplement(Base):
    __tablename__ = "inquiry_supplements"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("inquiry_sessions.id"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (Index("ix_inquiry_supplements_session", "session_id"),)
