from typing import Annotated

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, SessionDep
from app.core.schemas import Envelope
from app.modules.couples.deps import CurrentCouple
from app.modules.diaries import service
from app.modules.diaries.schemas import DiaryCreate, DiaryOut, DiaryUpdate

router = APIRouter(prefix="/diaries", tags=["diaries"])


@router.post("", response_model=Envelope[DiaryOut])
async def create(
    body: DiaryCreate, user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[DiaryOut]:
    diary = await service.create(session, couple, user, body)
    return Envelope(data=DiaryOut.model_validate(diary))


@router.get("", response_model=Envelope[list[DiaryOut]])
async def list_diaries(
    couple: CurrentCouple,
    session: SessionDep,
    mode: Annotated[str | None, Query(pattern="^(shared|personal)$")] = None,
    event_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Envelope[list[DiaryOut]]:
    diaries = await service.list_diaries(
        session, couple, mode=mode, event_id=event_id, limit=limit, offset=offset
    )
    return Envelope(data=[DiaryOut.model_validate(d) for d in diaries])


@router.get("/{diary_id}", response_model=Envelope[DiaryOut])
async def get_one(
    diary_id: int, couple: CurrentCouple, session: SessionDep
) -> Envelope[DiaryOut]:
    return Envelope(data=DiaryOut.model_validate(await service.get_one(session, couple, diary_id)))


@router.put("/{diary_id}", response_model=Envelope[DiaryOut])
async def update(
    diary_id: int,
    body: DiaryUpdate,
    user: CurrentUser,
    couple: CurrentCouple,
    session: SessionDep,
) -> Envelope[DiaryOut]:
    diary = await service.update(session, couple, user, diary_id, body)
    return Envelope(data=DiaryOut.model_validate(diary))


@router.delete("/{diary_id}", response_model=Envelope[None])
async def delete(
    diary_id: int, user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[None]:
    await service.delete(session, couple, user, diary_id)
    return Envelope()
