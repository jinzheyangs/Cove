"""站内通知表结构。

当前只有站内通知（App 内列表 + 未读数）；
厂商推送通道需要额外接入，不在这一层。

通知内容由业务服务生成，不直接引用秘密/日记正文，
避免通知列表变成隐私内容的旁路。
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Notification(Base):
    """一条通知。

    生命周期：创建（未读）-> 被读取（is_read=True）。
    没有删除接口，通知随时间自然沉淀。
    """

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # 收件人
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    # 业务类型，例如 secret.unlocked / coin_apply.approved
    type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(200))
    # 简短补充说明；不要放敏感正文
    content: Mapped[str | None] = mapped_column(Text)
    # 关联业务对象，前端可据此跳转
    related_type: Mapped[str | None] = mapped_column(String(50))
    related_id: Mapped[int | None] = mapped_column(BigInteger)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        # 「我的未读通知」和未读数都走这个索引
        Index("ix_notifications_user_read", "user_id", "is_read"),
    )
