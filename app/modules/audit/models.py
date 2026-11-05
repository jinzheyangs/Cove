"""审计日志表结构。

原则：
- 只记录「谁、何时、做了什么」，不记录任何隐私内容
- detail 里可以放数量、原因等元信息，但不要放秘密/日记正文
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AuditLog(Base):
    """一条敏感操作记录。

    目前已接入：绑定/解绑、销毁秘密、撤销模拟TA授权、注销账号。
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("couples.id"))
    # 操作人。注销账号后记录仍保留，但用户行已匿名化
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    # 动作名，例如 couple.bind / secret.destroy
    action: Mapped[str] = mapped_column(String(50))
    # 被操作对象的类型和 id，例如 ("secret", 12)
    target_type: Mapped[str | None] = mapped_column(String(50))
    target_id: Mapped[int | None] = mapped_column(BigInteger)
    # 结构化元信息：数量、原因等。不要放隐私正文
    detail: Mapped[dict | None] = mapped_column(JSONB)
    # 来源 IP 和请求 ID，便于追溯
    ip: Mapped[str | None] = mapped_column(String(64))
    request_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        # 「我的操作记录」和「某段关系的操作记录」都会按时间倒序查
        Index("ix_audit_logs_user_created", "user_id", "created_at"),
        Index("ix_audit_logs_couple_created", "couple_id", "created_at"),
    )
