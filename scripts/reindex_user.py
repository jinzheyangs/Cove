"""从 PG 全量重建某个用户的向量索引。

用法：
    uv run python scripts/reindex_user.py <couple_id> <user_id>

适用场景：
- Chroma 数据丢失
- 更换 embedding 模型（维度变化时必须重建）
- 怀疑索引和原文不一致
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.db import SessionLocal  # noqa: E402
from app.modules.ai.indexing import reindex_user  # noqa: E402


async def main(couple_id: int, user_id: int) -> None:
    async with SessionLocal() as session:
        await reindex_user(session, couple_id, user_id)
    print(f"reindexed couple={couple_id} user={user_id}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        raise SystemExit(1)
    asyncio.run(main(int(sys.argv[1]), int(sys.argv[2])))
