"""FastAPI 依赖：会话与当前用户。

`CurrentUser` / `SessionDep` 是所有业务路由的入口依赖。

请求链路：
1. 请求头 `Authorization: Bearer eyJxxx`
2. `CurrentUser` → 调用 `get_current_user`
3. 提取 token → decode_access_token（JWT_SECRET 验签）→ user_id
4. 拿到 `SessionDep`（AsyncSession，底层走连接池 engine）→ repo 查 User
5. 校验通过，绑定日志上下文，把 user 传给路由
6. 路由拿 user、session，调用 service/repository 做业务
   （比如加密保存日记，调用 AESGCM 加密函数）
"""

from typing import Annotated

import structlog
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import AppError
from app.core.security import decode_access_token
from app.modules.users import repository as user_repo
from app.modules.users.models import User

# auto_error=False：没带 token 时返回 None，由我们抛统一格式的 401，
# 而不是让 FastAPI 自己返回 403。
_bearer = HTTPBearer(auto_error=False)

# 路由里写 `session: SessionDep` 即可拿到当前请求的数据库会话
SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: SessionDep,
) -> User:
    """解析 Bearer token 并取出用户。

    失败场景统一返回 401，不区分“没带 token / token 过期 / 用户不存在”，
    避免给攻击者提供额外信息。

    成功后把 user_id 绑到 structlog 上下文，
    这样这个请求后续的所有日志都会自动带上用户 id。
    """
    if credentials is None:
        raise AppError("未登录", code=401, status_code=401)

    try:
        user_id = decode_access_token(credentials.credentials)
    except Exception as exc:  # noqa: BLE001 - 任何解码失败都视为未登录
        raise AppError("登录已失效，请重新登录", code=401, status_code=401) from exc

    # 每次都查库，确保用户被注销后 token 立即失效
    user = await user_repo.get_by_id(session, user_id)
    if user is None:
        raise AppError("用户不存在", code=401, status_code=401)

    # 之后的日志自动带上 user_id
    structlog.contextvars.bind_contextvars(user_id=user.id)
    return user


# 路由里写 `user: CurrentUser` 即可拿到已登录用户
CurrentUser = Annotated[User, Depends(get_current_user)]
