"""业务层：争吵模式、伤害熔断与强制复盘。

熔断只提示、不判定对错，也不阻断发送——被系统指责只会让冲突升级。
"""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.conflicts import repository as repo
from app.modules.conflicts.models import ConflictMessage, ConflictSession
from app.modules.conflicts.schemas import SessionDetailOut
from app.modules.couples.models import Couple
from app.modules.users.models import User

# 极端人身攻击词。宁可少判，也不要误伤正常表达。
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
    return any(word in text for word in _ATTACK_WORDS)


def _couple_user_ids(couple: Couple) -> list[int]:
    return [couple.user1_id, couple.user2_id]


async def start(session: AsyncSession, couple: Couple) -> ConflictSession:
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
    conflict = await repo.get_session(session, session_id)
    if conflict is None or conflict.couple_id != couple.id:
        raise AppError("对话不存在", code=12002, status_code=404)
    if conflict.status != "reviewing":
        raise AppError("现在还不能复盘，请先结束这段对话", code=12006, status_code=409)

    existing = await repo.get_review(session, conflict.id, user.id)
    if existing is not None:
        existing.want_to_be_understood = want
        existing.heard_partner_need = heard
    else:
        await repo.add_review(
            session,
            session_id=conflict.id,
            user_id=user.id,
            want=want,
            heard=heard,
        )

    await session.flush()
    submitted = await repo.count_reviews(
        session, conflict.id, _couple_user_ids(couple)
    )
    if submitted >= 2:
        conflict.status = "closed"

    await session.commit()
    await session.refresh(conflict)
    return conflict


async def get_detail(
    session: AsyncSession, couple: Couple, session_id: int
) -> SessionDetailOut:
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
