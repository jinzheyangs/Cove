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


class CoinAccount(Base):
    """金币余额。

    这是缓存，真相在 coin_transactions。任何时候对不上，以流水重算为准。
    """

    __tablename__ = "coin_accounts"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), primary_key=True
    )
    balance: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("balance >= 0", name="ck_coin_accounts_non_negative"),
    )


class CoinTransaction(Base):
    """金币流水。

    约定：
    - from_user_id IS NULL  -> 系统发行（赠与、奖励）
    - to_user_id   IS NULL  -> 销毁（消费）
    - 两边都填              -> 转账（暂未使用）
    """

    __tablename__ = "coin_transactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("couples.id"), index=True
    )
    type: Mapped[str] = mapped_column(String(20))
    from_user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    to_user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    actor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    amount: Mapped[int] = mapped_column(BigInteger)
    ref_type: Mapped[str | None] = mapped_column(String(30))
    ref_id: Mapped[int | None] = mapped_column(BigInteger)
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True)
    remark: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_coin_tx_amount_positive"),
        CheckConstraint(
            "from_user_id IS NOT NULL OR to_user_id IS NOT NULL",
            name="ck_coin_tx_has_party",
        ),
        CheckConstraint(
            "from_user_id IS NULL OR to_user_id IS NULL OR from_user_id <> to_user_id",
            name="ck_coin_tx_distinct_parties",
        ),
        Index("ix_coin_tx_to_user", "to_user_id"),
        Index("ix_coin_tx_from_user", "from_user_id"),
    )
