"""把历史明文数据加密成 v1 格式。

用法：
    uv run python scripts/encrypt_existing_data.py

只处理需要加密的列；已经是 v1: 开头的数据会跳过。
运行前请先备份数据库。
"""

import asyncio
import sys
from pathlib import Path

# 让脚本直接运行时也能 import app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.core.crypto import encrypt  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402

TARGETS = [
    ("secrets", "content"),
    ("diaries", "title"),
    ("diaries", "content"),
    ("daily_answers", "answer"),
    ("bills", "remark"),
]


async def main() -> None:
    async with SessionLocal() as session:
        for table, column in TARGETS:
            rows = await session.execute(
                text(
                    f"SELECT id, {column} AS value FROM {table} "
                    f"WHERE {column} IS NOT NULL AND {column} <> '' "
                    f"AND {column} NOT LIKE 'v1:%'"
                )
            )
            updated = 0
            for row in rows:
                await session.execute(
                    text(f"UPDATE {table} SET {column} = :value WHERE id = :id"),
                    {"value": encrypt(row.value), "id": row.id},
                )
                updated += 1

            if updated:
                await session.commit()
            print(f"{table}.{column}: encrypted {updated} rows")


if __name__ == "__main__":
    asyncio.run(main())
