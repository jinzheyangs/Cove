"""每日心情的 HTTP 接口。"""

from fastapi import APIRouter

from app.core.deps import CurrentUser, SessionDep
from app.core.schemas import Envelope
from app.modules.couples.deps import CurrentCouple
from app.modules.mood import service
from app.modules.mood.schemas import MoodCreate, MoodPairOut

router = APIRouter(prefix="/mood", tags=["mood"])


@router.get("", response_model=Envelope[MoodPairOut])
async def today(
    user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[MoodPairOut]:
    """今日双方心情。没记录时 mine/partner 为 null。"""
    return Envelope(data=await service.today_view(session, couple, user))


@router.post("", response_model=Envelope[MoodPairOut])
async def save(
    body: MoodCreate,
    user: CurrentUser,
    couple: CurrentCouple,
    session: SessionDep,
) -> Envelope[MoodPairOut]:
    """提交或修改今天的心情，返回更新后的双方视图。"""
    return Envelope(data=await service.save_mood(session, couple, user, body))
