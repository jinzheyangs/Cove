"""争吵模式的表结构。

会话状态机：
    ongoing --cool--> cooling --end--> reviewing --双方提交--> closed
    ongoing --------end--------------------^

消息和复盘内容都加密存储——这是整个产品里最敏感的数据之一。
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
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.types import EncryptedText


class ConflictSession(Base):
    """一次争吵会话。

    同一对伴侣同时只能有一个未关闭的会话。
    """

    __tablename__ = "conflict_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("couples.id"))
    # ongoing / cooling / reviewing / closed
    status: Mapped[str] = mapped_column(
        String(20), default="ongoing", server_default="ongoing"
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # 结束交流、进入复盘的时间
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "status IN ('ongoing', 'cooling', 'reviewing', 'closed')",
            name="ck_conflict_sessions_status",
        ),
        Index("ix_conflict_sessions_couple", "couple_id", "status"),
    )


class ConflictMessage(Base):
    """一条对话消息。

    flagged 表示命中了伤害词，但消息照常保存、照常展示：
    系统只提示，不替用户删话，也不判定谁对谁错。
    """

    __tablename__ = "conflict_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("conflict_sessions.id")
    )
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(EncryptedText)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (Index("ix_conflict_messages_session", "session_id"),)


class ConflictReview(Base):
    """复盘。

    两个问题必须回答，每人每条会话只能提交一份：
    - 我刚才最想被理解的是什么？
    - 我听到的对方的需求是什么？

    唯一约束 (session_id, user_id) 保证不会重复插入。
    """

    __tablename__ = "conflict_reviews"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("conflict_sessions.id")
    )
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    want_to_be_understood: Mapped[str] = mapped_column(EncryptedText)
    heard_partner_need: Mapped[str] = mapped_column(EncryptedText)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("session_id", "user_id", name="uq_conflict_reviews_session_user"),
    )
