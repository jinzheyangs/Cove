"""模拟TA 的 HTTP 接口。"""

from fastapi import APIRouter

from app.core.deps import CurrentUser, SessionDep
from app.core.schemas import Envelope
from app.modules.couples.deps import CurrentCouple
from app.modules.simta import service
from app.modules.simta.schemas import (
    ChatRequest,
    ChatResponse,
    ConsentRequest,
    PersonaStateOut,
    SettingsRequest,
)

router = APIRouter(prefix="/sim-ta", tags=["sim-ta"])


@router.get("", response_model=Envelope[PersonaStateOut])
async def state(
    user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[PersonaStateOut]:
    """查看双方的授权状态和自己的忠实度设置。"""
    return Envelope(data=await service.get_state(session, couple, user))


@router.put("/consent", response_model=Envelope[PersonaStateOut])
async def set_consent(
    body: ConsentRequest, user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[PersonaStateOut]:
    """开启 / 撤销「用我的数据做模拟」的授权。

    撤销后对方立刻无法和你的分身对话。
    """
    await service.set_consent(session, couple, user, body.authorized)
    return Envelope(data=await service.get_state(session, couple, user))


@router.put("/settings", response_model=Envelope[PersonaStateOut])
async def set_settings(
    body: SettingsRequest, user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[PersonaStateOut]:
    """切换忠实度：更接近真实 / 更理想化。"""
    await service.set_fidelity(session, couple, user, body.fidelity)
    return Envelope(data=await service.get_state(session, couple, user))


@router.post("/chat", response_model=Envelope[ChatResponse])
async def chat(
    body: ChatRequest, user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[ChatResponse]:
    """和对方的分身对话。

    需要对方已授权；回复里必须带 disclaimer。
    """
    return Envelope(data=await service.chat(session, couple, user, body.message))
