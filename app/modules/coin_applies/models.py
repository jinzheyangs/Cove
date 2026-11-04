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
    """金币申请：本人发起，对方审批后由系统发行。"""

    __tablename__ = "coin_applies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("couples.id"))
    applicant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    amount: Mapped[int] = mapped_column(BigInteger)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending"
    )
    decided_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
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
        Index("ix_coin_applies_applicant_status", "applicant_id", "status"),
        Index("ix_coin_applies_couple", "couple_id"),
    )
