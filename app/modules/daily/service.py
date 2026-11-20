"""业务层：每日一问。

题库存在 `daily_questions` 表里，取题按日期确定性地算 —— 零 AI 成本，
改题直接改库，不用改代码、不用重启。
这是整个产品里成本最低、但对留存最关键的模块。
"""

import random
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import today
from app.modules.couples.models import Couple
from app.modules.daily import repository as repo
from app.modules.daily.models import DailyQuestion
from app.modules.daily.schemas import DailyOut
from app.modules.users.models import User

# 建库用的种子题库（scripts/seed_daily_questions.py 会把它灌进 daily_questions）。
# 运行时不读这份常量：日常出题只看库，所以改题改库就够了。
SEED_QUESTIONS = [
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
    # —— 扩充段：题库越短，回环越快；下面这些让一轮变得更长
    "今天有什么小事想跟我分享？",
    "你有没有想过我们两三年后的样子？",
    "你觉得我们现在最缺的是什么？",
    "有什么事你一直想让我知道，只是怕说出来麻烦我？",
    "今天身体感觉怎么样，累不累？",
    "你最近在偷偷期待什么？",
    "有没有哪首歌最近让你想起我？",
    "你最想让我为你做的一件小事是什么？",
    "你觉得我们之间最不需要解释的是什么？",
    "最近一次你笑出声，是因为什么？",
    "有什么事你想让我陪你一起拖延一下？",
    "我有什么习惯，是你希望我别改的？",
    "今天如果只记住一件事，你想记住什么？",
    "你最想和我一起吃的一道菜是什么？",
    "你觉得我什么时候最好看？",
    "最近有什么事让你觉得我们在变好？",
    "有哪件事你希望我们固定成一个小仪式？",
    "你觉得我们适合一起养点什么？",
    "最近你心里有没有一句没说出口的谢谢？",
    "如果明天放假，你最想怎么过？",
    "你最近有没有哪张照片，舍不得删？",
    "你觉得我们最像老夫老妻的瞬间是什么时候？",
    "你今天想被我夸哪一句？",
    "你希望我们的下一个纪念日怎么过？",
]


# 取题算法在 2026-11-14 换过。这天之前作答的日子必须继续走老映射：
# 答案表里冗余存了当天的题面，换了映射就会出现「卡片上的题」和「答过的那道题」对不上。
# LEGACY_SEED 就是老的前 24 句，只服务历史那一段，不会随库里的改动而变。
ANCHOR = date(2026, 11, 14)
LEGACY_COUNT = 24
LEGACY_SEED = SEED_QUESTIONS[:LEGACY_COUNT]


def _legacy_question(day: date) -> str:
    return LEGACY_SEED[day.toordinal() % LEGACY_COUNT]


def _round_order(round_i: int, n: int) -> list[int]:
    """某一轮的出题顺序。

    用轮次当种子做确定性洗牌：同一轮所有人、双方看到的是同一张表，
    但每轮的顺序都不一样 —— 第一轮走完，第二轮不会照着上轮重播一遍。
    """
    order = list(range(n))
    random.Random(round_i * 48271 + 9176).shuffle(order)
    return order


def pick_question(day: date, pool: list[str]) -> str:
    """按日期从给定题库里确定性地选题：同一天两人拿到同一题，一轮之内绝不重复。

    - 老日子走老映射，历史答案不受影响。
    - 新日子从 ANCHOR 起算，每 n 天一轮，轮内乱序各取一次；
      轮与轮之间重新洗牌，所以不会「n 天一到，从头再来一遍」。
    """
    if day < ANCHOR or not pool:
        return _legacy_question(day)
    n = len(pool)
    round_i, idx = divmod((day - ANCHOR).days, n)
    return pool[_round_order(round_i, n)[idx]]


async def question_pool(session: AsyncSession) -> list[str]:
    """库里在架的题，按 sort_order 排。停用某题只要 is_active=false。

    每次都现查：改库后立刻生效，不做缓存。
    """
    rows = await session.execute(
        select(DailyQuestion.text)
        .where(DailyQuestion.is_active.is_(True))
        .order_by(DailyQuestion.sort_order, DailyQuestion.id)
    )
    pool = [r[0] for r in rows]
    # 库里被人清空了也别让首页崩：退回种子题库
    return pool or list(SEED_QUESTIONS)


async def question_for_day(session: AsyncSession, day: date) -> str:
    if day < ANCHOR:
        return _legacy_question(day)
    return pick_question(day, await question_pool(session))


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
    question = await question_for_day(session, day)

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
        question=await question_for_day(session, day),
        answer=text,
    )
    await session.commit()
    return await today_view(session, couple, user)
