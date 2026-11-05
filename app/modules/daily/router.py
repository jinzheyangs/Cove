"""每日一问的 HTTP 接口。"""

from fastapi import APIRouter

from app.core.deps import CurrentUser, SessionDep
from app.core.schemas import Envelope
from app.modules.couples.deps import CurrentCouple
from app.modules.daily import service
from app.modules.daily.schemas import AnswerCreate, DailyOut

router = APIRouter(prefix="/daily", tags=["daily"])


@router.get("", response_model=Envelope[DailyOut])
async def today(
    user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[DailyOut]:
    """今日问题与回答。没回答过时 my_answer 为 null。"""
    return Envelope(data=await service.today_view(session, couple, user))


@router.post("", response_model=Envelope[DailyOut])
async def answer(
    body: AnswerCreate, user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[DailyOut]:
    """提交或修改今天的回答，返回更新后的视图。"""
    return Envelope(data=await service.answer(session, couple, user, body.answer))
