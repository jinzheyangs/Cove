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
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class CoupleInvite(Base):
    __tablename__ = "couple_invites"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    inviter_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    code: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    status: Mapped[str] = mapped_column(
        String(20), default="active", server_default="active"
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Couple(Base):
    __tablename__ = "couples"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user1_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    user2_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(
        String(20), default="active", server_default="active"
    )
    bind_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    unbound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        # user1 永远是小 id，保证 (A,B) 和 (B,A) 不会建成两行
        CheckConstraint("user1_id < user2_id", name="ck_couples_ordered"),
        # 同一用户同时只能有一段 active 关系（数据库层兜底）
        Index(
            "uq_active_couple_u1",
            "user1_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        Index(
            "uq_active_couple_u2",
            "user2_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )
