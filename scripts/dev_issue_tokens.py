"""本地调试用：给指定用户直接签发一对 token（不走密码校验）。

只用于本地两个窗口互相调试，不改数据库里的密码，也不移除任何登录态。

用法：
    python scripts/dev_issue_tokens.py 8 3

生产环境会直接拒绝：这个脚本能绕过密码拿到任意用户的 token，
只该存在开发机上。
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
from app.modules.users import service as user_service  # noqa: E402
from app.modules.users.models import User  # noqa: E402


async def main(user_ids: list[int]) -> None:
    async with SessionLocal() as session:
        for uid in user_ids:
            user = await session.get(User, uid)
            if user is None:
                print(f"{uid}|MISSING||")
                continue
            access, refresh = await user_service.issue_tokens(session, user)
            print(f"{uid}|{user.nickname}|{access}|{refresh}")
        await session.commit()


if __name__ == "__main__":
    if settings.ENV == "prod":
        raise SystemExit("生产环境禁止使用 dev_issue_tokens.py")
    ids = [int(x) for x in sys.argv[1:]] or [8, 3]
    asyncio.run(main(ids))
