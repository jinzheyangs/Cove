from typing import Annotated

from fastapi import Depends

from app.core.deps import CurrentUser, SessionDep
from app.core.errors import AppError
from app.modules.couples import repository as repo
from app.modules.couples.models import Couple


async def get_current_couple(user: CurrentUser, session: SessionDep) -> Couple:
    couple = await repo.get_active_by_user(session, user.id)
    if couple is None:
        raise AppError("还没有绑定伴侣", code=3001, status_code=409)
    return couple


CurrentCouple = Annotated[Couple, Depends(get_current_couple)]
