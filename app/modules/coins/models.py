"""金币账户与流水的表结构。

整个金币系统的核心约定：
- **流水是唯一真相**，账户余额只是缓存
- 赠与 = 系统发行（from_user_id 为 NULL）
- 消费 = 销毁（to_user_id 为 NULL）
- 金币不是货币，不能在两人之间转账
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


class CoinAccount(Base):
    """金币余额（缓存）。

    这是缓存，真相在 coin_transactions。
    任何时候发现对不上，都从流水重算，以流水为准。
    worker 每天 03:17 会做一次全量对账。

    CHECK (balance >= 0) 是最后一道防线：
    即使业务代码漏了锁或判断，数据库也不会允许负余额。
    """

    __tablename__ = "coin_accounts"

    # 用 user_id 当主键：一个用户最多一个账户
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
    """金币流水（唯一真相）。

    字段语义：
    - from_user_id IS NULL  -> 系统发行（赠与、申请通过、奖励）
    - to_user_id   IS NULL  -> 销毁（消费）
    - 两边都填              -> 转账（当前产品不使用）

    余额重算方式：
        sum(amount where to_user_id = 我) - sum(amount where from_user_id = 我)

    actor_id 是「谁发起了这笔操作」，和 from/to 不是一回事：
    赠与是系统发行给 B，但发起人是 A，所以 from 为空、actor 为 A。
    """

    __tablename__ = "coin_transactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # 所有金币都发生在某段关系内，方便按关系隔离和统计
    couple_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("couples.id"), index=True
    )
    # gift / consume / apply / reward
    type: Mapped[str] = mapped_column(String(20))
    # 出金币的一方；为空表示系统发行
    from_user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    # 收金币的一方；为空表示销毁
    to_user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    # 发起这笔操作的人
    actor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    # 永远为正数，方向由 from/to 表达
    amount: Mapped[int] = mapped_column(BigInteger)
    # 关联的业务对象，例如 ('secret', 12)
    ref_type: Mapped[str | None] = mapped_column(String(30))
    ref_id: Mapped[int | None] = mapped_column(BigInteger)
    # 客户端或服务端生成的幂等键。唯一索引保证重复提交只生效一次
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True)
    remark: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_coin_tx_amount_positive"),
        # 至少有一方，否则这笔流水没有意义
        CheckConstraint(
            "from_user_id IS NOT NULL OR to_user_id IS NOT NULL",
            name="ck_coin_tx_has_party",
        ),
        # 不允许自己转给自己
        CheckConstraint(
            "from_user_id IS NULL OR to_user_id IS NULL OR from_user_id <> to_user_id",
            name="ck_coin_tx_distinct_parties",
        ),
        # 余额重算和流水列表都会按这两列过滤
        Index("ix_coin_tx_to_user", "to_user_id"),
        Index("ix_coin_tx_from_user", "from_user_id"),
    )
