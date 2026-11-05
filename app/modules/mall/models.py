from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class MallItem(Base):
    __tablename__ = "mall_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("couples.id"))
    creator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    price_coins: Mapped[int] = mapped_column(BigInteger)
    approved_price: Mapped[int | None] = mapped_column(BigInteger)
    max_orders: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending"
    )
    approver_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    reject_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("price_coins > 0", name="ck_mall_items_price_positive"),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'offline')",
            name="ck_mall_items_status",
        ),
        Index("ix_mall_items_couple_status", "couple_id", "status"),
    )


class MallOrder(Base):
    __tablename__ = "mall_orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("mall_items.id"))
    couple_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("couples.id"))
    buyer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    price: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending"
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'completed', 'cancelled')", name="ck_mall_orders_status"
        ),
        Index("ix_mall_orders_couple", "couple_id"),
        Index("ix_mall_orders_buyer", "buyer_id"),
    )
