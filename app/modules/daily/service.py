"""业务层：每日一问。

用固定题库按日期取题，零 AI 成本，也不需要等模型。
这是整个产品里成本最低、但对留存最关键的模块。
"""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import today
from app.modules.couples.models import Couple
from app.modules.daily import repository as repo
from app.modules.daily.schemas import DailyOut
from app.modules.users.models import User

# 题库写死，避免依赖外部服务。改题库不会影响历史记录，
# 因为答案表里冗余存了当天的题目文案。
QUESTIONS = [
    "今天有没有哪一刻，你突然觉得有我在挺好？",
    "最近有什么事你一直想说，但还没找到机会？",
    "你希望我多问你的哪一件事？",
    "如果今天可以重来一次，你想改哪个瞬间？",
    "最近哪句话让你觉得被理解了？",
    "你最近在为什么事情悄悄用力？",
    "有什么事你其实希望我主动一点？",
    "最近有没有什么小事让你有点委屈？",
    "你最想和我一起去做、但一直没做的事是什么？",
    "你最近一次觉得被爱，是什么时候？",
    "如果用一个词形容这周的你，会是什么？",
    "有什么事你希望我不要替你做决定？",
    "你最近在担心什么，但还没说出口？",
    "你觉得我们最近最舒服的时刻是什么时候？",
    "有什么是我做得不错、你希望我继续保持的？",
    "你希望我们吵架时，我记住哪一件事？",
    "最近有没有什么事让你觉得被忽略了？",
    "你最近想被怎么安慰？",
    "如果现在可以许一个关于我们的愿望，会是什么？",
    "你今天最需要的是什么？",
    "有什么话你一直想对过去的自己说？",
    "你觉得我最近有什么变化吗？",
    "最近有没有什么事，你希望我陪你一起面对？",
    "你今天想对我说一句什么？",
]


def question_for(day: date) -> str:
    """按日期确定性地选题。

    用 toordinal 取模：同一天两个人拿到同一题，
    不同天才换题，且不需要任何存储。
    """
    return QUESTIONS[day.toordinal() % len(QUESTIONS)]


def _partner_id(couple: Couple, user_id: int) -> int:
    """关系里的另一个人。"""
    return couple.user2_id if couple.user1_id == user_id else couple.user1_id


async def today_view(
    session: AsyncSession, couple: Couple, user: User
) -> DailyOut:
    """今日问题 + 双方回答。

    对方答案只在自己已回答后才返回。
    """
    day = today()
    question = question_for(day)

    mine = await repo.get_answer(session, couple.id, user.id, day)
    theirs = await repo.get_answer(
        session, couple.id, _partner_id(couple, user.id), day
    )

    return DailyOut(
        day=day,
        question=question,
        my_answer=mine.answer if mine else None,
        partner_answer=theirs.answer if (mine and theirs) else None,
    )


async def answer(
    session: AsyncSession, couple: Couple, user: User, text: str
) -> DailyOut:
    """提交或修改今天的回答，返回最新视图。"""
    day = today()
    await repo.upsert_answer(
        session,
        couple_id=couple.id,
        user_id=user.id,
        day=day,
        question=question_for(day),
        answer=text,
    )
    await session.commit()
    return await today_view(session, couple, user)
