"""业务层：争吵模式、伤害熔断与强制复盘。

设计原则：
- 熔断只提示、不判定对错，也不阻断发送——被系统指责只会让冲突升级
- 复盘是关闭会话的前置条件，但不强制立即写：卡在生气时只会产出假话
"""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.queue import enqueue
from app.modules.conflicts import repository as repo
from app.modules.conflicts.models import ConflictMessage, ConflictSession
from app.modules.conflicts.schemas import SessionDetailOut
from app.modules.couples.models import Couple
from app.modules.users.models import User

# 极端人身攻击词。宁可少判，也不要误伤正常表达。
# 关键词表是最低成本的方案；未来可以换成小模型，但不应由系统判定对错。
_ATTACK_WORDS = (
    "废物",
    "垃圾",
    "去死",
    "傻逼",
    "贱人",
    "神经病",
    "恶心死了",
    "后悔跟你",
    "你有病",
    "滚出去",
)

GENTLE_PROMPT = (
    "先停一下。这句话可能会伤到对方。"
    "要不要先说说：你刚才最希望被理解的是什么？"
)


def contains_attack(text: str) -> bool:
    """是否命中伤害词。

    纯字符串匹配，不做语义判断：
    误判的代价（指责用户）比漏判更高，所以宁可选保守的词表。
    """
    return any(word in text for word in _ATTACK_WORDS)


def _couple_user_ids(couple: Couple) -> list[int]:
    """关系里的两个人。"""
    return [couple.user1_id, couple.user2_id]


async def start(session: AsyncSession, couple: Couple) -> ConflictSession:
    """发起一次争吵会话。

    同一时间只允许一个未关闭的会话，
    避免多个会话并行导致复盘和上下文混乱。
    """
    existing = await repo.get_active_session(session, couple.id)
    if existing is not None:
        raise AppError("已经有一个进行中的对话", code=12001, status_code=409)

    conflict = await repo.create_session(session, couple.id)
    await session.commit()
    await session.refresh(conflict)
    return conflict


async def send_message(
    session: AsyncSession, couple: Couple, user: User, session_id: int, content: str
) -> tuple[ConflictMessage, str | None]:
    """发送一条消息。

    命中伤害词时只返回一句温和提示（gentle_prompt），
    消息照常保存、照常展示，不阻断交流。

    Returns:
        (消息, 提示文案或 None)
    """
    conflict = await repo.get_session(session, session_id)
    if conflict is None or conflict.couple_id != couple.id:
        raise AppError("对话不存在", code=12002, status_code=404)
    if conflict.status not in ("ongoing", "cooling"):
        raise AppError("这段对话已经不在交流阶段了", code=12003, status_code=409)

    flagged = contains_attack(content)
    message = await repo.add_message(
        session,
        session_id=conflict.id,
        user_id=user.id,
        content=content,
        flagged=flagged,
    )
    await session.commit()
    await session.refresh(message)
    return message, (GENTLE_PROMPT if flagged else None)


async def cool(session: AsyncSession, couple: Couple, session_id: int) -> ConflictSession:
    """进入冷静期。只允许从 ongoing 转。"""
    conflict = await repo.get_session(session, session_id)
    if conflict is None or conflict.couple_id != couple.id:
        raise AppError("对话不存在", code=12002, status_code=404)
    if conflict.status != "ongoing":
        raise AppError("只有进行中的对话可以进入冷静期", code=12004, status_code=409)

    conflict.status = "cooling"
    await session.commit()
    await session.refresh(conflict)
    return conflict


async def end(session: AsyncSession, couple: Couple, session_id: int) -> ConflictSession:
    """结束交流，进入复盘阶段。

    结束后不能再发消息，必须先完成复盘才能关闭会话。
    """
    conflict = await repo.get_session(session, session_id)
    if conflict is None or conflict.couple_id != couple.id:
        raise AppError("对话不存在", code=12002, status_code=404)
    if conflict.status not in ("ongoing", "cooling"):
        raise AppError("当前状态不能结束对话", code=12005, status_code=409)

    conflict.status = "reviewing"
    conflict.ended_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(conflict)
    return conflict


async def submit_review(
    session: AsyncSession,
    couple: Couple,
    user: User,
    session_id: int,
    want: str,
    heard: str,
) -> ConflictSession:
    """提交复盘。

    同一个人重复提交会覆盖上一次（方便修改措辞）。
    双方都提交后，会话自动关闭。
    """
    conflict = await repo.get_session(session, session_id)
    if conflict is None or conflict.couple_id != couple.id:
        raise AppError("对话不存在", code=12002, status_code=404)
    if conflict.status != "reviewing":
        raise AppError("现在还不能复盘，请先结束这段对话", code=12006, status_code=409)

    existing = await repo.get_review(session, conflict.id, user.id)
    if existing is not None:
        existing.want_to_be_understood = want
        existing.heard_partner_need = heard
        review_id = existing.id
    else:
        review = await repo.add_review(
            session,
            session_id=conflict.id,
            user_id=user.id,
            want=want,
            heard=heard,
        )
        review_id = review.id

    await session.flush()
    submitted = await repo.count_reviews(
        session, conflict.id, _couple_user_ids(couple)
    )
    if submitted >= 2:
        conflict.status = "closed"

    await session.commit()
    await session.refresh(conflict)
    # 复盘是模拟TA 的重要上下文，提交后异步重建索引
    await enqueue("index_review", review_id)
    return conflict


async def get_detail(
    session: AsyncSession, couple: Couple, session_id: int
) -> SessionDetailOut:
    """会话详情：状态 + 消息 + 复盘。

    消息和复盘都是解密后的明文。
    """
    conflict = await repo.get_session(session, session_id)
    if conflict is None or conflict.couple_id != couple.id:
        raise AppError("对话不存在", code=12002, status_code=404)

    messages = await repo.list_messages(session, conflict.id)
    reviews = await repo.list_reviews(session, conflict.id)

    return SessionDetailOut(
        id=conflict.id,
        status=conflict.status,
        started_at=conflict.started_at,
        ended_at=conflict.ended_at,
        messages=[
            {
                "id": m.id,
                "user_id": m.user_id,
                "content": m.content,
                "flagged": m.flagged,
                "created_at": m.created_at,
            }
            for m in messages
        ],
        reviews=[
            {
                "user_id": r.user_id,
                "want_to_be_understood": r.want_to_be_understood,
                "heard_partner_need": r.heard_partner_need,
                "created_at": r.created_at,
            }
            for r in reviews
        ],
    )
