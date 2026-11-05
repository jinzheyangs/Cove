"""商城表结构。

商品流：
    pending --approve--> approved --offline--> offline
    pending --reject---> rejected

订单流：
    pending --complete--> completed
"""

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
    """一件可兑换的商品 / 服务。

    上架需要对方确认价格：
    price_coins 是创建者的建议价，approved_price 是双方最终认可的价格。
    实际成交以 approved_price 为准。
    """

    __tablename__ = "mall_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("couples.id"))
    # 服务提供方，也是审批时不能自审的人
    creator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    # 创建者建议价
    price_coins: Mapped[int] = mapped_column(BigInteger)
    # 审批后最终价；审批人可以直接沿用建议价
    approved_price: Mapped[int | None] = mapped_column(BigInteger)
    # 可兑换次数，None 表示不限
    max_orders: Mapped[int | None] = mapped_column(BigInteger)
    # pending / approved / rejected / offline
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
    """一次兑换。

    价格在购买时快照到订单里：
    之后商品改价不会影响已产生的订单。
    """

    __tablename__ = "mall_orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("mall_items.id"))
    couple_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("couples.id"))
    # 花金币的一方
    buyer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    # 成交价快照
    price: Mapped[int] = mapped_column(BigInteger)
    # pending / completed / cancelled
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
