"""模拟TA 的检索层。

优先走向量检索（RAG）：
    用户问题 -> embedding -> Chroma top-k -> 上下文片段

以下情况自动退回「最近记录」模式：
- embedding 未配置
- Chroma 不可用
- 检索结果为空

退回逻辑保证：即使 AI 基础设施没配好，模拟TA 仍然能用，
只是上下文从「语义相关」退化成「最近写的」。
"""

import asyncio

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.agent.models import ChatMemory
from app.modules.ai import embeddings, vectorstore
from app.modules.diaries.models import Diary

logger = structlog.get_logger("retrieval")

# 回退模式的预算
DIARY_LIMIT = 10
EXCERPT = 200
# 对话记忆：命中几块，回退时给最近几块
MEMORY_TOP_K = 3
# 前置检索最多给这么久：超时就退回「最近记录」。
# 检索慢不该让一句「在吗」等上十秒。
QUERY_TIMEOUT = 2.5


def _excerpt(text: str) -> str:
    """压缩成一行并截断。"""
    text = text.strip().replace("\n", " ")
    return text if len(text) <= EXCERPT else text[:EXCERPT] + "…"


async def recent_context(
    session: AsyncSession, couple_id: int, target_user_id: int
) -> list[str]:
    """回退模式：取对方最近的日记。

    只读取该用户自己写的内容（日记作者是 TA）。
    """
    fragments: list[str] = []

    diaries = await session.scalars(
        select(Diary)
        .where(
            Diary.couple_id == couple_id,
            Diary.author_id == target_user_id,
        )
        .order_by(Diary.id.desc())
        .limit(DIARY_LIMIT)
    )
    for diary in diaries:
        tags = f"（情绪：{'、'.join(diary.mood_tags)}）" if diary.mood_tags else ""
        fragments.append(f"[日记] {_excerpt(diary.content)}{tags}")

    return fragments


async def collect_context(
    session: AsyncSession,
    couple_id: int,
    target_user_id: int,
    query_text: str | None = None,
) -> list[str]:
    """收集模拟的上下文。

    Args:
        query_text: 用户当前说的话。有值时走向量检索，
            为空或未配置时退回最近记录。
    """
    if query_text and embeddings.is_configured():
        try:
            vector = await embeddings.embed_one(query_text) #转成向量
            documents = await vectorstore.query(
                couple_id, target_user_id, vector, settings.RAG_TOP_K
            )   #去检索
            if documents:
                return documents
            logger.info(
                "rag.empty_result",
                couple_id=couple_id,
                user_id=target_user_id,
            )
        except Exception as exc:  # noqa: BLE001 - 检索失败不应阻断对话
            logger.warning("rag.query_failed", error=repr(exc))

    return await recent_context(session, couple_id, target_user_id) #兜底用


async def collect_memory(
    session: AsyncSession,
    couple_id: int,
    owner_id: int,
    query_text: str | None = None,
) -> list[str]:
    """检索「我和分身之前聊过的内容」。

    和 collect_context 分开：那里的片段是 TA 的记录（日记、导入的聊天），
    这里的片段是我自己的对话记忆，两者在提示词里要分开写，
    否则模型会把我说过的话当成 TA 的口吻。

    没配 embedding 时退回「最近的几块」，至少记住最近聊过什么。
    """
    if query_text and embeddings.is_configured():
        try:
            vector = await embeddings.embed_one(query_text)
            documents = await vectorstore.query(
                couple_id, owner_id, vector, MEMORY_TOP_K
            )
            if documents:
                return documents
            logger.info("rag.memory_empty", couple_id=couple_id, user_id=owner_id)
        except Exception as exc:  # noqa: BLE001 - 检索失败不应阻断对话
            logger.warning("rag.memory_query_failed", error=repr(exc))

    return await recent_memory(session, couple_id, owner_id)


async def recent_memory(
    session: AsyncSession,
    couple_id: int,
    owner_id: int,
    limit: int = MEMORY_TOP_K,
) -> list[str]:
    """回退模式：取最近的几块对话记忆。"""
    rows = list(
        await session.scalars(
            select(ChatMemory)
            .where(ChatMemory.couple_id == couple_id, ChatMemory.owner_id == owner_id)
            .order_by(ChatMemory.day.desc(), ChatMemory.seq.desc())
            .limit(limit)
        )
    )
    return [row.text for row in reversed(rows)]


async def collect_both(
    session: AsyncSession,
    couple_id: int,
    target_user_id: int,
    owner_id: int,
    query_text: str | None = None,
) -> tuple[list[str], list[str]]:
    """一次把两路上下文都取回来：TA 的记录 + 我的对话记忆。

    模拟TA 的首字延迟几乎全花在这里：同一句话被向量化了两次，
    两次 Chroma 查询还得排队。现在只算一次向量、两路并发查，
    整段检索超过 QUERY_TIMEOUT 就各自退回「最近记录」。
    """
    target_docs: list[str] = []
    memory_docs: list[str] = []

    if query_text and embeddings.is_configured():
        vector: list[float] | None = None
        try:
            vector = await asyncio.wait_for(
                embeddings.embed_one(query_text), timeout=QUERY_TIMEOUT
            )
        except Exception as exc:  # noqa: BLE001 - 超时/失败都退回最近记录
            logger.warning("rag.embed_failed", error=repr(exc))

        if vector:
            try:
                target_docs, memory_docs = await asyncio.wait_for(
                    asyncio.gather(
                        vectorstore.query(
                            couple_id, target_user_id, vector, settings.RAG_TOP_K
                        ),
                        vectorstore.query(
                            couple_id, owner_id, vector, MEMORY_TOP_K
                        ),
                    ),
                    timeout=QUERY_TIMEOUT,
                )
            except Exception as exc:  # noqa: BLE001 - 同上，不阻断对话
                logger.warning("rag.query_failed", error=repr(exc))
                target_docs, memory_docs = [], []

    if not target_docs:
        target_docs = await recent_context(session, couple_id, target_user_id)
    if not memory_docs:
        memory_docs = await recent_memory(session, couple_id, owner_id)
    return target_docs, memory_docs
