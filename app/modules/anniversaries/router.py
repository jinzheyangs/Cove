"""纪念日倒计时的 HTTP 接口。"""

from fastapi import APIRouter

from app.core.deps import CurrentUser, SessionDep
from app.core.schemas import Envelope
from app.modules.anniversaries import service
from app.modules.anniversaries.schemas import (
    AnniversaryCreate,
    AnniversaryOut,
    AnniversaryUpdate,
)
from app.modules.couples.deps import CurrentCouple

router = APIRouter(prefix="/anniversaries", tags=["anniversaries"])


@router.get("", response_model=Envelope[list[AnniversaryOut]])
async def list_anniversaries(
    couple: CurrentCouple, session: SessionDep
) -> Envelope[list[AnniversaryOut]]:
    """全部倒计时：在一起、双方生日、自定义纪念日。

    按剩余天数从近到远排序；已经过去的一次性事件排在最后。
    """
    entries = await service.list_entries(session, couple)
    return Envelope(data=entries)


@router.post("", response_model=Envelope[AnniversaryOut])
async def create_anniversary(
    body: AnniversaryCreate,
    user: CurrentUser,
    couple: CurrentCouple,
    session: SessionDep,
) -> Envelope[AnniversaryOut]:
    """新建自定义纪念日。

    repeat_yearly=true 表示每年重复；false 表示一次性事件。
    """
    entry = await service.create(session, couple, user, body)
    return Envelope(data=entry)


@router.put("/{anniversary_id}", response_model=Envelope[AnniversaryOut])
async def update_anniversary(
    anniversary_id: int,
    body: AnniversaryUpdate,
    couple: CurrentCouple,
    session: SessionDep,
) -> Envelope[AnniversaryOut]:
    """修改自定义纪念日。共同纪念日双方都能改。"""
    entry = await service.update(session, couple, anniversary_id, body)
    return Envelope(data=entry)


@router.delete("/{anniversary_id}", response_model=Envelope[None])
async def delete_anniversary(
    anniversary_id: int, couple: CurrentCouple, session: SessionDep
) -> Envelope[None]:
    """删除自定义纪念日。"""
    await service.delete(session, couple, anniversary_id)
    return Envelope()
