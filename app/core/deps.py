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

_bearer = HTTPBearer(auto_error=False)

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: SessionDep,
) -> User:
    if credentials is None:
        raise AppError("未登录", code=401, status_code=401)

    try:
        user_id = decode_access_token(credentials.credentials)
    except Exception as exc:  # noqa: BLE001 - 任何解码失败都视为未登录
        raise AppError("登录已失效，请重新登录", code=401, status_code=401) from exc

    user = await user_repo.get_by_id(session, user_id)
    if user is None:
        raise AppError("用户不存在", code=401, status_code=401)

    # 之后的日志自动带上 user_id
    structlog.contextvars.bind_contextvars(user_id=user.id)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
