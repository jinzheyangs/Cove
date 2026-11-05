from fastapi import APIRouter

from app.core.deps import CurrentUser, SessionDep
from app.core.schemas import Envelope
from app.modules.privacy import service
from app.modules.privacy.schemas import DeleteAccountRequest

router = APIRouter(prefix="/privacy", tags=["privacy"])


@router.post("/delete", response_model=Envelope[None])
async def delete_account(
    body: DeleteAccountRequest, user: CurrentUser, session: SessionDep
) -> Envelope[None]:
    await service.delete_account(session, user, body.password)
    return Envelope()


@router.get("/export", response_model=Envelope[dict])
async def export_data(user: CurrentUser, session: SessionDep) -> Envelope[dict]:
    return Envelope(data=await service.export_data(session, user))
