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

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.ai import embeddings, vectorstore
from app.modules.conflicts.models import ConflictReview, ConflictSession
from app.modules.diaries.models import Diary

logger = structlog.get_logger("retrieval")

# 回退模式的预算
DIARY_LIMIT = 10
REVIEW_LIMIT = 5
EXCERPT = 200


def _excerpt(text: str) -> str:
    """压缩成一行并截断。"""
    text = text.strip().replace("\n", " ")
    return text if len(text) <= EXCERPT else text[:EXCERPT] + "…"


async def recent_context(
    session: AsyncSession, couple_id: int, target_user_id: int
) -> list[str]:
    """回退模式：取对方最近的日记和复盘。

    只读取该用户自己写的内容：
    - 日记：作者是 TA
    - 复盘：提交人是 TA
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

    reviews = await session.scalars(
        select(ConflictReview)
        .join(ConflictSession, ConflictSession.id == ConflictReview.session_id)
        .where(
            ConflictSession.couple_id == couple_id,
            ConflictReview.user_id == target_user_id,
        )
        .order_by(ConflictReview.id.desc())
        .limit(REVIEW_LIMIT)
    )
    for review in reviews:
        fragments.append(
            f"[复盘] 最想被理解：{_excerpt(review.want_to_be_understood)}；"
            f"听到的需求：{_excerpt(review.heard_partner_need)}"
        )

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
            vector = await embeddings.embed_one(query_text)
            documents = await vectorstore.query(
                couple_id, target_user_id, vector, settings.RAG_TOP_K
            )
            if documents:
                return documents
            logger.info(
                "rag.empty_result",
                couple_id=couple_id,
                user_id=target_user_id,
            )
        except Exception as exc:  # noqa: BLE001 - 检索失败不应阻断对话
            logger.warning("rag.query_failed", error=repr(exc))

    return await recent_context(session, couple_id, target_user_id)
