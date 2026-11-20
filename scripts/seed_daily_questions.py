"""把种子题库灌进 daily_questions（可重复运行，不会插重复行）。

用法：
    .venv\\Scripts\\python.exe scripts\\seed_daily_questions.py

建表也在这里做（CREATE TABLE IF NOT EXISTS 语义），新库跑这一个脚本就够。
之后加减题不用再跑脚本，直接改库：
    # 加一道（排最后，下一轮才轮到它）
    INSERT INTO daily_questions (text, sort_order) VALUES ('今天有什么小事想分享？', 100);
    # 下架一道（不再出题，历史回答还在）
    UPDATE daily_questions SET is_active = false WHERE text = '……';
    # 改文案
    UPDATE daily_questions SET text = '……' WHERE id = 7;
"""

import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.db import Base, SessionLocal, engine  # noqa: E402
from app.modules.daily.models import DailyQuestion  # noqa: E402
from app.modules.daily.service import SEED_QUESTIONS  # noqa: E402


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[DailyQuestion.__table__])

    added = 0
    async with SessionLocal() as session:
        existing = set((await session.execute(select(DailyQuestion.text))).scalars())
        for i, text in enumerate(SEED_QUESTIONS, start=1):
            if text in existing:
                continue
            session.add(DailyQuestion(text=text, sort_order=i, is_active=True))
            added += 1
        await session.commit()
        total = len((await session.execute(select(DailyQuestion.id))).all())
        active = len(
            (
                await session.execute(
                    select(DailyQuestion.id).where(DailyQuestion.is_active.is_(True))
                )
            ).all()
        )

    print(f"新增 {added} 道；库里共 {total} 道，在架 {active} 道")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
