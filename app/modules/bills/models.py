"""恋爱账本表结构。

设计取向：这是「我们一起为这段关系投入了什么」的记录，
不是分账工具，也不是谁付出更多的排行榜。

因此：
- 非金钱付出（时间/精力/情绪）只记事件，不记数量
- 统计接口只输出共同视角的汇总
"""

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
    """一条支出或付出记录。

    两个独立维度，不要混淆：
    - scope：这笔钱算共同支出还是个人支出（双方都可见）
    - is_private：这条记录是否只对记账人可见
    """

    __tablename__ = "bills"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("couples.id"))
    # 记账人。隐私记录也只有这个人能看到
    payer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    # 只有 money 类型有金额；非金钱付出为 NULL
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    category: Mapped[str] = mapped_column(String(50))
    # money / time / energy / emotion
    type: Mapped[str] = mapped_column(String(20), default="money", server_default="money")
    # shared / personal
    scope: Mapped[str] = mapped_column(String(20), default="shared", server_default="shared")
    # 仅记账人可见
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    # 备注可能包含敏感信息，加密存储
    remark: Mapped[str | None] = mapped_column(EncryptedText)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "type IN ('money', 'time', 'energy', 'emotion')", name="ck_bills_type"
        ),
        CheckConstraint("scope IN ('shared', 'personal')", name="ck_bills_scope"),
        # 金额可以没有，但不能是负数
        CheckConstraint("amount IS NULL OR amount >= 0", name="ck_bills_amount"),
        Index("ix_bills_couple_created", "couple_id", "created_at"),
    )
