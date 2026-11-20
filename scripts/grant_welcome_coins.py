"""给「已经绑定过、但当时没发见面礼」的情侣补发初始金币。

绑定流程现在会自己发（app/modules/couples/service.py 里的 WELCOME_COINS），
这个脚本只处理历史数据：按 couple 找出两边余额都是 0 的，各补一笔。
幂等：幂等键是 welcome:<couple_id>:<user_id>，重复跑不会多发。

用法：
    python scripts/grant_welcome_coins.py --dry-run     # 只看会发给谁
    python scripts/grant_welcome_coins.py               # 真的发
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402
from app.modules.coins import repository as coin_repo  # noqa: E402
from app.modules.coins import service as coin_service  # noqa: E402
from app.modules.couples.models import Couple  # noqa: E402
from app.modules.couples.service import WELCOME_COINS  # noqa: E402


async def main(commit: bool) -> None:
    async with SessionLocal() as session:
        couples = (
            await session.scalars(select(Couple).where(Couple.status == "active"))
        ).all()

        for couple in couples:
            for uid in (couple.user1_id, couple.user2_id):
                key = f"welcome:{couple.id}:{uid}"
                if await coin_repo.find_by_idempotency_key(session, key) is not None:
                    continue
                balance = await coin_service.get_balance(session, uid)
                if balance != 0:
                    # 已经有钱的人不补：说明他走的是别的发放路径
                    print(f"skip couple={couple.id} user={uid} balance={balance}")
                    continue
                print(f"grant couple={couple.id} user={uid} +{WELCOME_COINS}")
                if commit:
                    await coin_service.mint_locked(
                        session,
                        couple_id=couple.id,
                        actor_id=uid,
                        recipient_id=uid,
                        amount=WELCOME_COINS,
                        tx_type="reward",
                        ref_type="couple",
                        ref_id=couple.id,
                        remark="新情侣见面礼（补发）",
                        idempotency_key=key,
                    )

        if commit:
            await session.commit()
            print("committed")
        else:
            await session.rollback()
            print("dry-run, nothing changed")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    asyncio.run(main(commit=not ap.parse_args().dry_run))
