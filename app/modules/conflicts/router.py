"""争吵模式的 HTTP 接口。

流程：
    POST /conflicts                 发起
    POST /conflicts/{id}/messages   交流（命中伤害词会附带提示）
    POST /conflicts/{id}/cool       冷静期
    POST /conflicts/{id}/end        结束交流，进入复盘
    POST /conflicts/{id}/review     提交复盘（双方都提交后自动关闭）
"""

from fastapi import APIRouter

from app.core.deps import CurrentUser, SessionDep
from app.core.schemas import Envelope
from app.modules.conflicts import service
from app.modules.conflicts.schemas import (
    MessageCreate,
    MessageOut,
    MessageSentOut,
    ReviewCreate,
    SessionDetailOut,
    SessionOut,
)
from app.modules.couples.deps import CurrentCouple

router = APIRouter(prefix="/conflicts", tags=["conflicts"])


@router.post("", response_model=Envelope[SessionOut])
async def start(couple: CurrentCouple, session: SessionDep) -> Envelope[SessionOut]:
    """发起会话。同一时间只能有一个未关闭的会话。"""
    conflict = await service.start(session, couple)
    return Envelope(data=SessionOut.model_validate(conflict))


@router.get("/{session_id}", response_model=Envelope[SessionDetailOut])
async def detail(
    session_id: int, couple: CurrentCouple, session: SessionDep
) -> Envelope[SessionDetailOut]:
    """查看会话详情：消息和复盘。"""
    return Envelope(data=await service.get_detail(session, couple, session_id))


@router.post("/{session_id}/messages", response_model=Envelope[MessageSentOut])
async def send_message(
    session_id: int,
    body: MessageCreate,
    user: CurrentUser,
    couple: CurrentCouple,
    session: SessionDep,
) -> Envelope[MessageSentOut]:
    """发送消息。

    命中伤害词时响应里会带 gentle_prompt，
    但消息本身仍然发送成功——不阻断。
    """
    message, prompt = await service.send_message(
        session, couple, user, session_id, body.content
    )
    return Envelope(
        data=MessageSentOut(
            message=MessageOut.model_validate(message), gentle_prompt=prompt
        )
    )


@router.post("/{session_id}/cool", response_model=Envelope[SessionOut])
async def cool(
    session_id: int, couple: CurrentCouple, session: SessionDep
) -> Envelope[SessionOut]:
    """进入冷静期。"""
    conflict = await service.cool(session, couple, session_id)
    return Envelope(data=SessionOut.model_validate(conflict))


@router.post("/{session_id}/end", response_model=Envelope[SessionOut])
async def end(
    session_id: int, couple: CurrentCouple, session: SessionDep
) -> Envelope[SessionOut]:
    """结束交流，进入复盘阶段。"""
    conflict = await service.end(session, couple, session_id)
    return Envelope(data=SessionOut.model_validate(conflict))


@router.post("/{session_id}/review", response_model=Envelope[SessionOut])
async def submit_review(
    session_id: int,
    body: ReviewCreate,
    user: CurrentUser,
    couple: CurrentCouple,
    session: SessionDep,
) -> Envelope[SessionOut]:
    """提交复盘。

    两个问题都必须回答。双方都提交后会话状态变为 closed。
    """
    conflict = await service.submit_review(
        session,
        couple,
        user,
        session_id,
        body.want_to_be_understood,
        body.heard_partner_need,
    )
    return Envelope(data=SessionOut.model_validate(conflict))
