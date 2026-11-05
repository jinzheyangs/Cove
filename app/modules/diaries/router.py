"""恋爱日记的 HTTP 接口。"""

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
    """新建日记。写同一件事时两个人传同一个 event_id。"""
    diary = await service.create(session, couple, user, body)
    return Envelope(data=service.to_out(diary))


@router.get("", response_model=Envelope[list[DiaryOut]])
async def list_diaries(
    couple: CurrentCouple,
    session: SessionDep,
    mode: Annotated[str | None, Query(pattern="^(shared|personal)$")] = None,
    event_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Envelope[list[DiaryOut]]:
    """列出日记。

    传 event_id 可以取到同一件事的两种视角。
    """
    diaries = await service.list_diaries(
        session, couple, mode=mode, event_id=event_id, limit=limit, offset=offset
    )
    return Envelope(data=[service.to_out(d) for d in diaries])


@router.get("/{diary_id}", response_model=Envelope[DiaryOut])
async def get_one(
    diary_id: int, couple: CurrentCouple, session: SessionDep
) -> Envelope[DiaryOut]:
    """读取单篇。只能读到本关系内的日记。"""
    diary = await service.get_one(session, couple, diary_id)
    return Envelope(data=service.to_out(diary))


@router.put("/{diary_id}", response_model=Envelope[DiaryOut])
async def update(
    diary_id: int,
    body: DiaryUpdate,
    user: CurrentUser,
    couple: CurrentCouple,
    session: SessionDep,
) -> Envelope[DiaryOut]:
    """部分更新。个人视角只有作者能改。"""
    diary = await service.update(session, couple, user, diary_id, body)
    return Envelope(data=service.to_out(diary))


@router.delete("/{diary_id}", response_model=Envelope[None])
async def delete(
    diary_id: int, user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[None]:
    """删除。个人视角只有作者能删。"""
    await service.delete(session, couple, user, diary_id)
    return Envelope()
