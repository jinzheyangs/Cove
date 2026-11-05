"""秘密树表结构。

一条秘密的生命周期：
    active --(被摘取且设置了阅后即焚)--> burned --(24h 后)--> 内容清空
    active --(作者主动销毁)------------> destroyed

content 使用 EncryptedText，数据库里是密文。
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.types import EncryptedText


class Secret(Base):
    """一条秘密。

    作者发布后，对方需要花金币才能摘取。
    作者自己不能摘取自己的秘密。
    """

    __tablename__ = "secrets"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("couples.id"))
    # 发布者。只有发布者能销毁它
    author_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    # 加密存储，ORM 读写自动加解密
    content: Mapped[str] = mapped_column(EncryptedText)
    # normal / deep。深度秘密默认更贵
    level: Mapped[str] = mapped_column(String(20), default="normal", server_default="normal")
    # 摘取需要消耗的金币，由作者设定
    cost_coins: Mapped[int] = mapped_column(BigInteger)
    # 读完后是否标记为已燃尽
    is_burn_after_read: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    # active / burned / destroyed
    status: Mapped[str] = mapped_column(String(20), default="active", server_default="active")
    # 谁摘取过、什么时候。只有两个人，所以单字段足够
    viewed_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("level IN ('normal', 'deep')", name="ck_secrets_level"),
        CheckConstraint(
            "status IN ('active', 'burned', 'destroyed')", name="ck_secrets_status"
        ),
        CheckConstraint("cost_coins > 0", name="ck_secrets_cost_positive"),
        # 「对方可摘取列表」按 couple + status 过滤
        Index("ix_secrets_couple_status", "couple_id", "status"),
        Index("ix_secrets_author", "author_id"),
    )
