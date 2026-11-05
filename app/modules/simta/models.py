"""模拟TA 的表结构。

两类记录：
- PersonaConsent：谁授权把自己的数据用于模拟
- PersonaSettings：发起模拟的人偏好哪种忠实度

授权是数据使用的前置条件：
对方撤销后，chat 接口会直接拒绝，不会再读取 TA 的任何内容。
"""

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
    """数据授权。

    默认 authorized=False：必须对方主动开启。
    撤销即停止使用，不保留任何派生数据。
    """

    __tablename__ = "persona_consents"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("couples.id"))
    # 被模拟的那个人
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    authorized: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        # 一段关系里，每个人只有一条授权记录
        UniqueConstraint("couple_id", "user_id", name="uq_persona_consents_couple_user"),
    )


class PersonaSettings(Base):
    """发起模拟的人对分身的偏好。

    fidelity:
    - faithful：尽量贴近真实记录，不确定就说不知道
    - idealized：更温和、更理想化的版本，但禁止做承诺
    """

    __tablename__ = "persona_settings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("couples.id"))
    # 谁在模拟别人
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
