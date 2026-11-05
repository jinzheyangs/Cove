"""把业务数据索引到向量库。

写入链路：
    日记 / 复盘 -> 切片 -> embedding -> Chroma
    chunk_index 表记录映射关系，用于增量更新和删除同步

设计原则：
- **PG 是真相**，Chroma 只是可重建的索引
- 内容没变就不重新 embedding（用 content_hash 判断），省调用费
- 没配置 embedding 时直接跳过，不影响业务写入
"""

import hashlib

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.ai import embeddings, vectorstore
from app.modules.ai.models import ChunkIndex
from app.modules.conflicts.models import ConflictReview, ConflictSession
from app.modules.diaries.models import Diary

logger = structlog.get_logger("indexing")


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    """按字符数切片。

    中文场景不按 token 切：不同模型的 tokenizer 不一样，
    按字符切更可控，也更容易解释。

    overlap 让相邻片段有重叠，避免一句话正好被切断后语义丢失。
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]

    step = max(1, size - overlap)
    chunks = []
    for start in range(0, len(text), step):
        chunk = text[start : start + size]
        if chunk:
            chunks.append(chunk)
        if start + size >= len(text):
            break
    return chunks


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


async def _delete_source(
    session: AsyncSession, source_type: str, source_id: int
) -> None:
    """删除某条业务数据的全部向量和映射。"""
    rows = list(
        await session.scalars(
            select(ChunkIndex).where(
                ChunkIndex.source_type == source_type,
                ChunkIndex.source_id == source_id,
            )
        )
    )
    if not rows:
        return

    await vectorstore.delete_ids([row.chroma_id for row in rows])
    await session.execute(
        delete(ChunkIndex).where(
            ChunkIndex.source_type == source_type,
            ChunkIndex.source_id == source_id,
        )
    )
    await session.commit()


async def _replace_source(
    session: AsyncSession,
    *,
    couple_id: int,
    user_id: int,
    source_type: str,
    source_id: int,
    text: str,
) -> None:
    """重建某条业务数据的索引。

    先删旧向量再写新的，保证不会出现「改了内容但旧片段还在」。
    """
    chunks = chunk_text(text, settings.RAG_CHUNK_SIZE, settings.RAG_CHUNK_OVERLAP)
    if not chunks:
        await _delete_source(session, source_type, source_id)
        return

    existing = list(
        await session.scalars(
            select(ChunkIndex)
            .where(
                ChunkIndex.source_type == source_type,
                ChunkIndex.source_id == source_id,
            )
            .order_by(ChunkIndex.chunk_no)
        )
    )

    digest = _hash(text)
    # 内容没变且切片数量一致，直接跳过，省一次 embedding 调用
    if len(existing) == len(chunks) and all(
        row.content_hash == digest for row in existing
    ):
        return

    if existing:
        await vectorstore.delete_ids([row.chroma_id for row in existing])
        await session.execute(
            delete(ChunkIndex).where(
                ChunkIndex.source_type == source_type,
                ChunkIndex.source_id == source_id,
            )
        )

    vectors = await embeddings.embed_texts(chunks)
    ids = [f"{source_type}:{source_id}:{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "couple_id": couple_id,
            "user_id": user_id,
            "source_type": source_type,
            "source_id": source_id,
            "chunk_no": i,
        }
        for i in range(len(chunks))
    ]
    await vectorstore.upsert(ids, vectors, chunks, metadatas)

    session.add_all(
        [
            ChunkIndex(
                couple_id=couple_id,
                user_id=user_id,
                source_type=source_type,
                source_id=source_id,
                chunk_no=i,
                chroma_id=ids[i],
                content_hash=digest,
            )
            for i in range(len(chunks))
        ]
    )
    await session.commit()


async def index_diary(session: AsyncSession, diary_id: int) -> None:
    """索引一篇日记。"""
    if not embeddings.is_configured():
        return

    diary = await session.get(Diary, diary_id)
    if diary is None:
        return

    parts = []
    if diary.title:
        parts.append(f"标题：{diary.title}")
    parts.append(diary.content)
    if diary.mood_tags:
        parts.append(f"情绪：{'、'.join(diary.mood_tags)}")

    await _replace_source(
        session,
        couple_id=diary.couple_id,
        user_id=diary.author_id,
        source_type="diary",
        source_id=diary.id,
        text="\n".join(parts),
    )


async def index_review(session: AsyncSession, review_id: int) -> None:
    """索引一份争吵复盘。"""
    if not embeddings.is_configured():
        return

    review = await session.get(ConflictReview, review_id)
    if review is None:
        return

    text = (
        f"最想被理解：{review.want_to_be_understood}\n"
        f"听到的需求：{review.heard_partner_need}"
    )
    # 复盘没有直接存 couple_id，需要通过 session 关联查一次
    conflict = await session.get(ConflictSession, review.session_id)
    if conflict is None:
        return

    await _replace_source(
        session,
        couple_id=conflict.couple_id,
        user_id=review.user_id,
        source_type="review",
        source_id=review.id,
        text=text,
    )


async def delete_diary_vectors(session: AsyncSession, diary_id: int) -> None:
    """删除一篇日记的索引。"""
    await _delete_source(session, "diary", diary_id)


async def delete_review_vectors(session: AsyncSession, review_id: int) -> None:
    """删除一份复盘的索引。"""
    await _delete_source(session, "review", review_id)


async def delete_user_vectors(
    session: AsyncSession, couple_id: int | None, user_id: int
) -> None:
    """删除某个用户的全部向量。

    - 撤销模拟TA 授权：传 couple_id，只删当前关系内的
    - 注销账号：传 None，删全量
    """
    await vectorstore.delete_for_user(couple_id, user_id)

    stmt = delete(ChunkIndex).where(ChunkIndex.user_id == user_id)
    if couple_id is not None:
        stmt = stmt.where(ChunkIndex.couple_id == couple_id)
    await session.execute(stmt)
    await session.commit()


async def reindex_user(
    session: AsyncSession, couple_id: int, user_id: int
) -> None:
    """从 PG 全量重建某个用户的索引。

    先删掉旧向量再重建，因此换 embedding 模型、Chroma 数据丢失时都能用。
    只依赖 PG 里的原文，Chroma 里有什么不影响结果。
    """
    await delete_user_vectors(session, couple_id, user_id)

    diaries = list(
        await session.scalars(
            select(Diary).where(
                Diary.couple_id == couple_id, Diary.author_id == user_id
            )
        )
    )
    for diary in diaries:
        await index_diary(session, diary.id)

    reviews = list(
        await session.scalars(
            select(ConflictReview)
            .join(ConflictSession, ConflictSession.id == ConflictReview.session_id)
            .where(
                ConflictSession.couple_id == couple_id,
                ConflictReview.user_id == user_id,
            )
        )
    )
    for review in reviews:
        await index_review(session, review.id)

    logger.info(
        "indexing.reindexed",
        couple_id=couple_id,
        user_id=user_id,
        diaries=len(diaries),
        reviews=len(reviews),
    )
