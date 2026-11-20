"""AI 对话服务的表结构。

- agent_conversations：一次多轮对话
- agent_messages：对话里的每条消息（加密）
- agent_actions：模型提议的写操作，等待用户确认
- chat_memories：对话切块后的长期记忆（比会话活得久）

会话默认保留 30 天，每次新消息顺延；过期由 worker 清理。
"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
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


class AgentConversation(Base):
    __tablename__ = "agent_conversations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("couples.id"))
    # 发起对话的人
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    # 被模拟的人（一定是 owner 的伴侣）
    target_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    # 会话标题，可能包含隐私，加密
    title: Mapped[str | None] = mapped_column(EncryptedText)
    # False 时不在服务端保存消息，客户端每次自己带 history
    persist: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    # 过期时间，由 worker 定期清理
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_agent_conversations_owner", "owner_id", "updated_at"),
        Index("ix_agent_conversations_expires", "expires_at"),
    )


class AgentMessage(Base):
    __tablename__ = "agent_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agent_conversations.id", ondelete="CASCADE")
    )
    # user = 用户说的话，assistant = 分身回的话
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(EncryptedText)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="ck_agent_messages_role"),
        Index("ix_agent_messages_conversation", "conversation_id", "id"),
    )


class AgentAction(Base):
    """Agent 提议的写操作，等待用户确认。

    模型只能创建 pending，不能直接执行。
    真正的写入由确认接口触发，保证是用户本人点的。
    """

    __tablename__ = "agent_actions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agent_conversations.id", ondelete="CASCADE")
    )
    # 发起对话的人，也只有这个人能确认
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    # create_todo / create_diary ...
    type: Mapped[str] = mapped_column(String(30))
    # 操作参数，JSON 字符串，加密存储
    payload: Mapped[str] = mapped_column(EncryptedText)
    # 执行结果，JSON 字符串，加密存储；用于幂等重放
    result: Mapped[str | None] = mapped_column(EncryptedText)
    # pending / confirmed / cancelled / expired
    status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'confirmed', 'cancelled', 'expired')",
            name="ck_agent_actions_status",
        ),
        Index("ix_agent_actions_conversation", "conversation_id"),
        Index("ix_agent_actions_user_status", "user_id", "status"),
    )


class ChatMemory(Base):
    """把「我和分身聊过的内容」切成块，作为长期记忆。

    会话本身 30 天就清了，记忆要活得更久，所以单独落表：
    PG 是真相，Chroma 只是它的索引，随时可重建。

    - day 按北京时间切天，同一天的对话落进同一批块
    - seq 是当天第几块，和 day 一起保证同一条会话重复处理时是覆盖而不是堆积
    """

    __tablename__ = "chat_memories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("couples.id"))
    # 记忆归属：谁跟分身聊的。检索时按它过滤，别人看不到你的对话
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    # 被模拟的人，用于将来区分「模拟谁」的记忆
    target_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    # 来源会话；不设外键，因为会话过期会被清理，记忆要留着
    conversation_id: Mapped[int] = mapped_column(BigInteger)
    day: Mapped[date] = mapped_column(Date)
    seq: Mapped[int] = mapped_column(BigInteger)
    # 块原文：日期头 + 每行带说话人，加密
    text: Mapped[str] = mapped_column(EncryptedText)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "conversation_id", "day", "seq", name="uq_chat_memory_conv_day_seq"
        ),
        Index("ix_chat_memory_owner_day", "owner_id", "day"),
    )
