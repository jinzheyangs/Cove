from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class PersonaConsent(Base):
    """谁授权把自己的数据用于模拟。撤销即停止使用。"""

    __tablename__ = "persona_consents"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("couples.id"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    authorized: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("couple_id", "user_id", name="uq_persona_consents_couple_user"),
    )


class PersonaSettings(Base):
    """发起模拟的人对「数字分身」的偏好。"""

    __tablename__ = "persona_settings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("couples.id"))
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    fidelity: Mapped[str] = mapped_column(
        String(20), default="faithful", server_default="faithful"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("couple_id", "owner_id", name="uq_persona_settings_couple_owner"),
        CheckConstraint(
            "fidelity IN ('faithful', 'idealized')", name="ck_persona_settings_fidelity"
        ),
    )
