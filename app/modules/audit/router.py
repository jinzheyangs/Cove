from typing import Annotated

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, SessionDep
from app.core.schemas import Envelope
from app.modules.audit import service
from app.modules.audit.schemas import AuditOut

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=Envelope[list[AuditOut]])
async def list_mine(
    user: CurrentUser,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Envelope[list[AuditOut]]:
    logs = await service.list_mine(session, user.id, limit, offset)
    return Envelope(data=[AuditOut.model_validate(log) for log in logs])
