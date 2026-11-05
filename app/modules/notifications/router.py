"""站内通知的 HTTP 接口。"""

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, SessionDep
from app.core.schemas import Envelope
from app.modules.notifications import service
from app.modules.notifications.schemas import NotificationOut, UnreadCountOut

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=Envelope[list[NotificationOut]])
async def list_mine(
    user: CurrentUser,
    session: SessionDep,
    unread_only: bool = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Envelope[list[NotificationOut]]:
    """列出通知。unread_only=true 时只返回未读。"""
    items = await service.list_mine(
        session, user.id, unread_only=unread_only, limit=limit, offset=offset
    )
    return Envelope(data=[NotificationOut.model_validate(i) for i in items])


@router.get("/unread-count", response_model=Envelope[UnreadCountOut])
async def unread_count(
    user: CurrentUser, session: SessionDep
) -> Envelope[UnreadCountOut]:
    """未读数，用于红点。"""
    return Envelope(data=UnreadCountOut(unread=await service.unread_count(session, user.id)))


@router.post("/{notification_id}/read", response_model=Envelope[dict])
async def mark_read(
    notification_id: int, user: CurrentUser, session: SessionDep
) -> Envelope[dict]:
    """标记单条已读。不是自己的通知不会更新。"""
    updated = await service.mark_read(session, user.id, notification_id)
    return Envelope(data={"updated": updated})


@router.post("/read-all", response_model=Envelope[dict])
async def mark_all_read(user: CurrentUser, session: SessionDep) -> Envelope[dict]:
    """全部标记已读。"""
    count = await service.mark_all_read(session, user.id)
    return Envelope(data={"updated": count})
