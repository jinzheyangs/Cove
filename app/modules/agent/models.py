"""AI 对话服务的表结构。

三张表：
- agent_conversations：一次多轮对话
- agent_messages：对话里的每条消息（加密）
- persona_profiles：从聊天记录提炼出的风格画像

会话默认保留 30 天，每次新消息顺延；过期由 worker 清理。
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
from sqlalchemy.dialects.postgresql import JSONB
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


class ChatImport(Base):
    """一次聊天记录导入。

    原始文件不落盘；解析出的消息存 chat_messages。
    """

    __tablename__ = "chat_imports"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("couples.id"))
    uploaded_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    filename: Mapped[str] = mapped_column(String(255))
    format: Mapped[str] = mapped_column(String(20))
    # processing / done / failed
    status: Mapped[str] = mapped_column(
        String(20), default="processing", server_default="processing"
    )
    total_messages: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    imported_messages: Mapped[int] = mapped_column(
        BigInteger, default=0, server_default="0"
    )
    indexed_windows: Mapped[int] = mapped_column(
        BigInteger, default=0, server_default="0"
    )
    # 解析失败或发送人对不上的条数
    skipped_messages: Mapped[int] = mapped_column(
        BigInteger, default=0, server_default="0"
    )
    error: Mapped[str | None] = mapped_column(EncryptedText)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "status IN ('processing', 'done', 'failed')", name="ck_chat_import_status"
        ),
        Index("ix_chat_imports_couple", "couple_id", "created_at"),
    )


class ChatMessage(Base):
    """一条聊天消息。内容加密。

    source_hash 用于去重：同一条消息重复导入时不会产生两份。
    """

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("couples.id"))
    import_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chat_imports.id"))
    # 能对上用户就填；对不上时只保留昵称
    sender_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    sender_name: Mapped[str] = mapped_column(String(100))
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    content: Mapped[str] = mapped_column(EncryptedText)
    msg_type: Mapped[str] = mapped_column(String(20), default="text", server_default="text")
    source_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("couple_id", "source_hash", name="uq_chat_message_hash"),
        Index("ix_chat_messages_couple_sender", "couple_id", "sender_id", "sent_at"),
    )


class PersonaProfile(Base):
    """某个用户的说话风格画像。

    由聊天记录导入后生成：
    - style_summary：一段自然语言描述，直接进 system prompt
    - samples_json：代表性原话，JSON 数组，加密
    - stats：统计指标（长度、表情率等），不含原文，明文存
    """

    __tablename__ = "persona_profiles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("couples.id"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    style_summary: Mapped[str | None] = mapped_column(EncryptedText)
    # JSON 数组字符串，加密
    samples_json: Mapped[str | None] = mapped_column(EncryptedText)
    # 纯统计，不含内容，可以明文
    stats: Mapped[dict | None] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("couple_id", "user_id", name="uq_persona_profile_couple_user"),
    )
