"""金币申请表结构。

流程：本人申请 -> 对方审批 -> 通过后由系统发行金币。
审批时对方可以改金额，所以「申请金额」和「实际发放金额」分开存。
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


class CoinApply(Base):
    """一条金币申请。

    状态机：
        pending --approve--> approved
        pending --reject---> rejected
    只有 pending 能被处理；重复审批会被服务层拒绝。
    """

    __tablename__ = "coin_applies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("couples.id"))
    # 发起申请的人，也是最终收金币的人
    applicant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    # 申请人希望获得的金额
    amount: Mapped[int] = mapped_column(BigInteger)
    # 做了什么、为什么值得这些金币
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending"
    )
    # 审批人（一定是伴侣，不可能是申请人自己）
    decided_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    # 实际发放金额。审批人可以把 100 改成 30
    approved_amount: Mapped[int | None] = mapped_column(BigInteger)
    decision_remark: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_coin_applies_amount_positive"),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')", name="ck_coin_applies_status"
        ),
        # 查「我有哪些待审批」和统计待审批数量都走这个索引
        Index("ix_coin_applies_applicant_status", "applicant_id", "status"),
        Index("ix_coin_applies_couple", "couple_id"),
    )
