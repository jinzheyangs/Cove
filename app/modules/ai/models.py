"""向量索引的映射表。

PG 是真相，Chroma 是可重建的索引。
这张表记录「哪条业务数据的第几段，对应 Chroma 里的哪个 id」，
用于增量更新、删除同步和重建索引。
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ChunkIndex(Base):
    __tablename__ = "chunk_index"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    couple_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("couples.id"))
    # 内容作者。检索时按这个过滤，保证只拿被模拟者自己的记录
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    # diary / chat
    source_type: Mapped[str] = mapped_column(String(30))
    source_id: Mapped[int] = mapped_column(BigInteger)
    chunk_no: Mapped[int] = mapped_column(BigInteger)
    # Chroma 里的向量 id，格式：{source_type}:{source_id}:{chunk_no}
    chroma_id: Mapped[str] = mapped_column(String(100), unique=True)
    # 原文哈希，内容没变就不重新 embedding，省调用费
    content_hash: Mapped[str] = mapped_column(String(64))
    indexed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "source_type", "source_id", "chunk_no", name="uq_chunk_source_no"
        ),
        Index("ix_chunk_couple_user", "couple_id", "user_id"),
    )
