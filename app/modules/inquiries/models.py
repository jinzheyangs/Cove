"""询问中心的表结构。

流程：
    collecting --双方都提交、生成--> ai_processing --AI 返回--> reviewing --关闭--> closed

所有文本字段（问题、AI 回复、双方想法）都加密存储。
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.types import EncryptedText


class InquirySession(Base):
    """一次共同提问。

    问题由任意一方提出；双方各自写下真实想法后，
    由 AI 做一次中立汇总。
    """

    __tablename__ = "inquiry_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("couples.id"))
    question: Mapped[str] = mapped_column(EncryptedText)
    # AI 的汇总结果，生成后写入
    ai_response: Mapped[str | None] = mapped_column(EncryptedText)
    # collecting / ai_processing / reviewing / closed
    status: Mapped[str] = mapped_column(
        String(20), default="collecting", server_default="collecting"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "status IN ('collecting', 'ai_processing', 'reviewing', 'closed')",
            name="ck_inquiry_sessions_status",
        ),
        Index("ix_inquiry_sessions_couple", "couple_id"),
    )


class InquiryInput(Base):
    """双方各自写下的真实想法。

    对外只返回内容，不返回 user_id：
    两个人之间匿名意义有限，但至少保证“谁说的”不会成为讨论焦点。
    唯一约束保证一人一条，重复提交是修改而不是新增。
    """

    __tablename__ = "inquiry_inputs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("inquiry_sessions.id"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(EncryptedText)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("session_id", "user_id", name="uq_inquiry_inputs_session_user"),
    )


class InquirySupplement(Base):
    """AI 回复之后的补充意见，可以有多条。"""

    __tablename__ = "inquiry_supplements"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("inquiry_sessions.id"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(EncryptedText)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (Index("ix_inquiry_supplements_session", "session_id"),)
