"""模拟TA 的检索层。

当前实现：从 PostgreSQL 里取对方最近的日记和争吵复盘作为上下文。
这是可替换的——换成 Chroma + embedding 只需要实现同样签名的函数，
业务层不用改。
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.conflicts.models import ConflictReview, ConflictSession
from app.modules.diaries.models import Diary

DIARY_LIMIT = 10
REVIEW_LIMIT = 5
EXCERPT = 200


def _excerpt(text: str) -> str:
    text = text.strip().replace("\n", " ")
    return text if len(text) <= EXCERPT else text[:EXCERPT] + "…"


async def collect_context(
    session: AsyncSession, couple_id: int, target_user_id: int
) -> list[str]:
    """收集某个用户在关系里留下的痕迹，作为模拟的依据。"""
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
