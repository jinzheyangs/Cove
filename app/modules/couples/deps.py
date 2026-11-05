"""情侣相关的依赖。"""

from typing import Annotated

from fastapi import Depends

from app.core.deps import CurrentUser, SessionDep
from app.core.errors import AppError
from app.modules.couples import repository as repo
from app.modules.couples.models import Couple


async def get_current_couple(user: CurrentUser, session: SessionDep) -> Couple:
    """要求当前用户已绑定伴侣。

    未绑定时返回 409 而不是 401：
    这是业务前置条件不满足，不是身份问题。
    """
    couple = await repo.get_active_by_user(session, user.id)
    if couple is None:
        raise AppError("还没有绑定伴侣", code=3001, status_code=409)
    return couple


# 所有情侣内业务（秘密、商城、日记……）都用它做前置依赖
CurrentCouple = Annotated[Couple, Depends(get_current_couple)]
