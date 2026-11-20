"""把业务数据索引到向量库。

写入链路：
    日记 -> 切片 -> embedding -> Chroma
    chunk_index 表记录映射关系，用于增量更新和删除同步

设计原则：
- **PG 是真相**，Chroma 只是可重建的索引
- 内容没变就不重新 embedding（用 content_hash 判断），省调用费
- 没配置 embedding 时直接跳过，不影响业务写入
"""

import hashlib
from datetime import date

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.time import TZ
from app.modules.agent.models import AgentConversation, AgentMessage, ChatMemory
from app.modules.ai import embeddings, vectorstore
from app.modules.ai.models import ChunkIndex
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

    先写新向量，再清理旧记录。顺序反过来的话，embedding 一失败/进程被杀，
    就变成「旧的已删、新的没写」，数据静默丢失且没人发现。
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
    # 内容没变且切片数量一致，通常可以跳过，省一次 embedding 调用。
    # 但要先跟 Chroma 核对：chunk_index 只是「我索引过」的记录，
    # 容器重建 / 卷丢数据 / 别处误删都会让向量实际不在，这时必须重建。
    if len(existing) == len(chunks) and all(
        row.content_hash == digest for row in existing
    ):
        expected = {row.chroma_id for row in existing}
        if await vectorstore.existing_ids(list(expected)) == expected:
            return
        logger.warning(
            "indexing.vectors_missing",
            source_type=source_type,
            source_id=source_id,
            expected=len(expected),
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

    # Chroma 的 HNSW 段偶尔不落盘：count 有、get 拿不到，检索就是「想不起来」。
    # 写完读回确认一次，丢就再写一遍，别等对账任务才发现。
    if await vectorstore.existing_ids(list(ids)) != set(ids):
        logger.warning(
            "indexing.upsert_not_durable",
            source_type=source_type,
            source_id=source_id,
            expected=len(ids),
        )
        await vectorstore.upsert(ids, vectors, chunks, metadatas)

    if existing:
        # 新向量已经落库，这时才动旧的；块数变少时多出来的 id 要删掉。
        # 反过来「先整体删再写」，embedding 一失败就是永久少几条。
        new_ids = set(ids)
        stale_ids = [row.chroma_id for row in existing if row.chroma_id not in new_ids]
        if stale_ids:
            await vectorstore.delete_ids(stale_ids)
        await session.execute(
            delete(ChunkIndex).where(
                ChunkIndex.source_type == source_type,
                ChunkIndex.source_id == source_id,
            )
        )

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


async def delete_diary_vectors(session: AsyncSession, diary_id: int) -> None:
    """删除一篇日记的索引。"""
    await _delete_source(session, "diary", diary_id)


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

    logger.info(
        "indexing.reindexed",
        couple_id=couple_id,
        user_id=user_id,
        diaries=len(diaries),
    )


# --------------------------------------------------------------------------
# 对话记忆：把「我和分身聊过的内容」切成块，长期留着
# --------------------------------------------------------------------------

# 一块最多多少字、最多几轮。太小检索命中没上下文，太大一块混了好几个话题
MEMORY_BLOCK_CHARS = 320
MEMORY_MAX_TURNS = 6
MEMORY_MAX_MESSAGES = 1000

_WEEKDAY = "一二三四五六日"


def _memory_block_text(day: date, lines: list[str]) -> str:
    """块头带日期，每行带说话人。

    日期必须进正文：模型看到「11 月 13 日」才知道那是上周的事，
    不然会把历史里的话当成今天刚说的。
    """
    head = f"{day.isoformat()} 周{_WEEKDAY[day.weekday()]}"
    return head + "\n" + "\n".join(lines)


def build_memory_blocks(
    messages: list[AgentMessage],
    owner_name: str,
    target_name: str,
) -> list[tuple[date, str]]:
    """把消息按「北京时间的一天 + 最多 6 轮」切成块，块之间不重叠。

    切块目标是「回忆事实」，所以和做 few-shot 的滑动窗口不同：
    不重叠，免得检索 top-k 被同一段反复占满。
    """
    blocks: list[tuple[date, str]] = []
    day: date | None = None
    lines: list[str] = []
    turns = 0

    def flush() -> None:
        nonlocal lines, turns
        if lines and day is not None:
            blocks.append((day, _memory_block_text(day, lines)))
        lines, turns = [], 0

    for message in messages:
        content = (message.content or "").strip()
        if not content:
            continue
        local = message.created_at
        if local.tzinfo is None:
            from datetime import UTC

            local = local.replace(tzinfo=UTC)
        local = local.astimezone(TZ)
        message_day = local.date()

        # 换天必封块；一天之内装满轮数或字数也封块
        if day is not None and message_day != day:
            flush()
        day = message_day

        who = owner_name if message.role == "user" else target_name
        if message.role == "user":
            turns += 1
        if lines and (
            turns > MEMORY_MAX_TURNS
            or sum(len(line) for line in lines) + len(content) > MEMORY_BLOCK_CHARS
        ):
            flush()
            day = message_day
        lines.append(f"{who}：{content}")

    flush()
    return blocks


async def index_chat_memories(
    session: AsyncSession, conversation_id: int, embed: bool = True
) -> int:
    """切块写进 chat_memories，并重建这些块的向量索引。

    embed=False 只落 PG（每轮回复后台调一次，不花 embedding 的网络时间），
    向量留给「离开页面」或每日兜底去建 —— 那时读到的块已经是最新的。

    即使 embedding 没配，块也会落 PG —— 之后配好了重跑一次就能补全，
    记忆本身不依赖向量库。
    """
    conversation = await session.get(AgentConversation, conversation_id)
    if conversation is None:
        return 0

    owner = await session.get(User, conversation.owner_id)
    target = await session.get(User, conversation.target_id)
    owner_name = owner.nickname if owner is not None else "我"
    target_name = target.nickname if target is not None else "TA"

    messages = list(
        await session.scalars(
            select(AgentMessage)
            .where(AgentMessage.conversation_id == conversation_id)
            .order_by(AgentMessage.id)
            .limit(MEMORY_MAX_MESSAGES)
        )
    )
    blocks = build_memory_blocks(messages, owner_name, target_name)

    # 同一条会话重复处理时按 (day, seq) 覆盖，不堆积
    existing = {
        (row.day, row.seq): row
        for row in await session.scalars(
            select(ChatMemory).where(ChatMemory.conversation_id == conversation_id)
        )
    }

    keep: set[tuple[date, int]] = set()
    for seq, (day, text) in enumerate(blocks):
        key = (day, seq)
        keep.add(key)
        row = existing.get(key)
        if row is None:
            row = ChatMemory(
                couple_id=conversation.couple_id,
                owner_id=conversation.owner_id,
                target_id=conversation.target_id,
                conversation_id=conversation_id,
                day=day,
                seq=seq,
                text=text,
            )
            session.add(row)
            await session.flush()
        elif row.text != text:
            row.text = text
            await session.flush()

    # 消息变少了（比如会话被裁）时，把多出来的块连同向量一起删掉
    for key, row in existing.items():
        if key not in keep:
            await _delete_source(session, "memory", row.id)
            await session.delete(row)
    await session.commit()

    if not embed or not embeddings.is_configured():
        return len(blocks)

    rows = list(
        await session.scalars(
            select(ChatMemory).where(ChatMemory.conversation_id == conversation_id)
        )
    )
    for row in rows:
        await _replace_source(
            session,
            couple_id=row.couple_id,
            user_id=row.owner_id,      # 记忆归属聊天的本人，检索时按他过滤
            source_type="memory",
            source_id=row.id,
            text=row.text,
        )

    logger.info(
        "indexing.memories",
        conversation_id=conversation_id,
        blocks=len(blocks),
        embedded=len(rows) if embeddings.is_configured() else 0,
    )
    return len(blocks)


async def reindex_memory(session: AsyncSession, memory_id: int) -> bool:
    """按 id 重建单块记忆的向量。对账任务用。"""
    row = await session.get(ChatMemory, memory_id)
    if row is None:
        return False
    await _replace_source(
        session,
        couple_id=row.couple_id,
        user_id=row.owner_id,
        source_type="memory",
        source_id=row.id,
        text=row.text,
    )
    return True


async def reconcile_vectors(session: AsyncSession) -> dict[str, int]:
    """和 Chroma 对一次账：补缺、清残留、删孤儿。

    Chroma 是容器内可重建的索引，宿主机磁盘满、容器非正常退出都可能让它少几条；
    chunk_index 记着「应该有哪些」，这里按记录重建，保证「说过的忘不掉」。

    三类问题分别处理：
    - 源数据已经不存在（日记被删）→ 记录和向量一起清
    - 记录在、向量缺 → 重新切块 embedding
    - 向量在、记录没了 → 当孤儿删掉

    Returns:
        {"repaired": 补回数, "stale": 清理的过期记录数, "orphans": 清理的孤儿数}
    """
    stats = {"repaired": 0, "stale": 0, "orphans": 0}

    rows = list(await session.scalars(select(ChunkIndex)))
    if not rows:
        return stats

    diary_ids = set(await session.scalars(select(Diary.id)))
    memory_ids = set(await session.scalars(select(ChatMemory.id)))

    stale = [
        row
        for row in rows
        if (row.source_type == "diary" and row.source_id not in diary_ids)
        or (row.source_type == "memory" and row.source_id not in memory_ids)
    ]
    if stale:
        await vectorstore.delete_ids([row.chroma_id for row in stale])
        await session.execute(
            delete(ChunkIndex).where(ChunkIndex.id.in_([row.id for row in stale]))
        )
        await session.commit()
        stats["stale"] = len(stale)
        stale_record_ids = {row.id for row in stale}
        rows = [row for row in rows if row.id not in stale_record_ids]

    expected = {row.chroma_id for row in rows}
    missing = expected - await vectorstore.existing_ids(list(expected))

    if missing and embeddings.is_configured():
        diary_sources = sorted(
            {r.source_id for r in rows if r.source_type == "diary" and r.chroma_id in missing}
        )
        for diary_id in diary_sources:
            try:
                await index_diary(session, diary_id)
                stats["repaired"] += sum(
                    1
                    for r in rows
                    if r.source_type == "diary"
                    and r.source_id == diary_id
                    and r.chroma_id in missing
                )
            except Exception as exc:  # noqa: BLE001 - 单篇失败不影响其它
                await session.rollback()
                logger.warning(
                    "indexing.reconcile_failed",
                    source_type="diary",
                    source_id=diary_id,
                    error=repr(exc),
                )

        memory_sources = sorted(
            {r.source_id for r in rows if r.source_type == "memory" and r.chroma_id in missing}
        )
        for memory_id in memory_sources:
            try:
                if await reindex_memory(session, memory_id):
                    stats["repaired"] += 1
            except Exception as exc:  # noqa: BLE001 - 单块失败不影响其它
                await session.rollback()
                logger.warning(
                    "indexing.reconcile_failed",
                    source_type="memory",
                    source_id=memory_id,
                    error=repr(exc),
                )

    orphans = await vectorstore.all_ids() - expected
    if orphans:
        await vectorstore.delete_ids(list(orphans))
        stats["orphans"] = len(orphans)

    logger.info("indexing.reconciled", **stats)
    return stats
