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
from app.modules.agent.models import ChatImport, ChatMessage
from app.modules.ai import embeddings, vectorstore
from app.modules.ai.models import ChunkIndex
from app.modules.conflicts.models import ConflictReview, ConflictSession
from app.modules.couples.models import Couple
from app.modules.diaries.models import Diary
from app.modules.users.models import User

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
    chunks = chunk_text(text, settings.RAG_CHUNK_SIZE, settings.RAG_CHUNK_OVERLAP)  #进行切分
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
    ids = [f"{source_type}:{source_id}:{i}" for i in range(len(chunks))]    #给这一批加上ids

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
    if not embeddings.is_configured():  #判断一下是否配置嵌入向量
        return

    diary = await session.get(Diary, diary_id)  #找出该id的日记
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


def _build_chat_windows(
    messages: list[ChatMessage], target_id: int, size: int = 4
) -> list[list[ChatMessage]]:
    """按对话窗口切片，窗口必须包含目标用户本人的发言。

    每条目标发言都生成一个窗口（带前面几条上下文），
    这样检索命中时能看到「对方说了什么 + TA 怎么回」。
    """
    windows: list[list[ChatMessage]] = []
    buffer: list[ChatMessage] = []

    for message in messages:
        if message.sender_id is None or message.msg_type != "text":
            continue
        buffer.append(message)
        if len(buffer) > size:
            buffer.pop(0)   #得出最新的4条
        if message.sender_id == target_id and len(buffer) >= 2:
            windows.append(list(buffer))

    return windows


def _cap_windows(
    windows: list[list[ChatMessage]], limit: int
) -> list[list[ChatMessage]]:
    """超过上限时均匀抽样，控制 embedding 成本。"""
    if len(windows) <= limit:
        return windows
    step = len(windows) / limit
    return [windows[int(i * step)] for i in range(limit)]


def _format_chat_window(
    window: list[ChatMessage],
    target_id: int,
    target_name: str,
    other_name: str,
) -> str:
    """标注每一句是谁说的。

    必须用真实昵称而不是「TA / 对方」：
    模型看到「对方」时不知道指的是谁，容易把用户自己的口吻当成模拟对象。
    """
    lines = []
    for message in window:
        who = target_name if message.sender_id == target_id else other_name
        lines.append(f"{who}：{message.content}")
    return "\n".join(lines)


async def index_chat_import(session: AsyncSession, import_id: int) -> int:
    """把一次导入的聊天记录切窗口、embedding、写 Chroma。

    Returns:
        写入的窗口数量。
    """
    if not embeddings.is_configured():      #看看是否配置embedding
        return 0

    import_row = await session.get(ChatImport, import_id)   #从主表看一下是否存在
    if import_row is None:
        return 0

    couple = await session.get(Couple, import_row.couple_id)    #查一下情侣关系是否正式
    if couple is None:
        return 0

    # 取双方昵称，用于给窗口里的每一句标注说话人
    users = {
        user.id: user
        for user in await session.scalars(
            select(User).where(User.id.in_([couple.user1_id, couple.user2_id]))
        )
    }

    messages = list(
        await session.scalars(
            select(ChatMessage)
            .where(
                ChatMessage.import_id == import_id,
                ChatMessage.msg_type == "text",
            )
            .order_by(ChatMessage.sent_at, ChatMessage.id)
        )
    )   #按时间顺序排好记录

    # 重建前先清掉这个导入已有的索引
    await delete_chat_import(session, import_id)

    window_no = 0       #窗口计数器
    for target_id in (couple.user1_id, couple.user2_id):
        other_id = (
            couple.user2_id if target_id == couple.user1_id else couple.user1_id
        )   #得出对方的id
        target_name = users[target_id].nickname if target_id in users else "TA"     #得到本人的名字
        other_name = users[other_id].nickname if other_id in users else "对方"      #得到对方的名字

        windows = _cap_windows(
            _build_chat_windows(messages, target_id), settings.RAG_CHAT_MAX_WINDOWS
        )
        texts = [
            _format_chat_window(window, target_id, target_name, other_name)
            for window in windows
        ]   #返回由块返回的字符串列表

        # 分批 embedding，避免单次请求过大
        for start in range(0, len(texts), 100):
            batch = texts[start : start + 100]
            vectors = await embeddings.embed_texts(batch)
            ids = [
                f"chat:{import_id}:{target_id}:{window_no + i}"
                for i in range(len(batch))
            ]
            metadatas = [
                {
                    "couple_id": import_row.couple_id,
                    "user_id": target_id,
                    "source_type": "chat",
                    "source_id": import_id,
                    "chunk_no": window_no + i,
                }
                for i in range(len(batch))
            ]
            await vectorstore.upsert(ids, vectors, batch, metadatas)
            session.add_all(
                [
                    ChunkIndex(
                        couple_id=import_row.couple_id,
                        user_id=target_id,
                        source_type="chat",
                        source_id=import_id,
                        chunk_no=window_no + i,
                        chroma_id=ids[i],
                        content_hash=_hash(batch[i]),
                    )
                    for i in range(len(batch))
                ]
            )
            window_no += len(batch)

    await session.commit()
    return window_no


async def delete_chat_import(session: AsyncSession, import_id: int) -> None:
    """删除一次导入对应的全部向量和映射。"""
    rows = list(
        await session.scalars(
            select(ChunkIndex).where(
                ChunkIndex.source_type == "chat",
                ChunkIndex.source_id == import_id,
            )
        )
    )
    if not rows:
        return

    await vectorstore.delete_ids([row.chroma_id for row in rows])
    await session.execute(
        delete(ChunkIndex).where(
            ChunkIndex.source_type == "chat",
            ChunkIndex.source_id == import_id,
        )
    )
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
