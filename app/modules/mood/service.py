"""业务层：每日心情。

和“每日一问”不同，心情不设“先回答才看对方”的门槛：
双方随时都能看到自己和对方今天的心情。
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import today
from app.modules.couples.models import Couple
from app.modules.mood import repository as repo
from app.modules.mood.schemas import MoodCreate, MoodOut, MoodPairOut
from app.modules.users.models import User


def _partner_id(couple: Couple, user_id: int) -> int:
    """关系里的另一个人。"""
    return couple.user2_id if couple.user1_id == user_id else couple.user1_id


def _to_out(rec) -> MoodOut:
    return MoodOut(
        id=rec.id,
        day=rec.day,
        user_id=rec.user_id,
        mood=rec.mood,
        level=rec.level,
        note=rec.note,
    )


async def today_view(
    session: AsyncSession, couple: Couple, user: User
) -> MoodPairOut:
    """今日双方心情，没记录时对应字段为 null。"""
    day = today()

    mine = await repo.get_record(session, couple.id, user.id, day)
    theirs = await repo.get_record(
        session, couple.id, _partner_id(couple, user.id), day
    )

    return MoodPairOut(
        day=day,
        mine=_to_out(mine) if mine else None,
        partner=_to_out(theirs) if theirs else None,
    )


async def save_mood(
    session: AsyncSession, couple: Couple, user: User, body: MoodCreate
) -> MoodPairOut:
    """提交或修改今天的心情，返回更新后的双方视图。"""
    await repo.upsert_record(
        session,
        couple_id=couple.id,
        user_id=user.id,
        day=today(),
        mood=body.mood,
        level=body.level,
        note=body.note,
    )
    await session.commit()
    return await today_view(session, couple, user)
