"""询问中心的 HTTP 接口。

流程：
    POST /inquiries                 发起
    POST /inquiries/{id}/input      各自写想法
    POST /inquiries/{id}/generate   双方都写完后生成 AI 分析
    POST /inquiries/{id}/supplement 补充意见
    POST /inquiries/{id}/close      关闭
    GET  /inquiries/{id}            查看
"""

from fastapi import APIRouter

from app.core.deps import CurrentUser, SessionDep
from app.core.schemas import Envelope
from app.modules.couples.deps import CurrentCouple
from app.modules.inquiries import service
from app.modules.inquiries.schemas import InputCreate, InquiryCreate, InquiryOut

router = APIRouter(prefix="/inquiries", tags=["inquiries"])


@router.post("", response_model=Envelope[dict])
async def create(
    body: InquiryCreate, couple: CurrentCouple, session: SessionDep
) -> Envelope[dict]:
    """发起询问。返回精简信息，完整内容走详情接口。"""
    item = await service.create(session, couple, body.question)
    return Envelope(data={"id": item.id, "question": item.question, "status": item.status})


@router.post("/{session_id}/input", response_model=Envelope[dict])
async def submit_input(
    session_id: int,
    body: InputCreate,
    user: CurrentUser,
    couple: CurrentCouple,
    session: SessionDep,
) -> Envelope[dict]:
    """提交自己的真实想法。collecting 阶段可反复修改。"""
    item = await service.submit_input(session, couple, user, session_id, body.content)
    return Envelope(data={"id": item.id, "status": item.status})


@router.post("/{session_id}/generate", response_model=Envelope[dict])
async def generate(
    session_id: int, couple: CurrentCouple, session: SessionDep
) -> Envelope[dict]:
    """触发 AI 汇总。双方都提交后才允许。"""
    item = await service.generate(session, couple, session_id)
    return Envelope(
        data={"id": item.id, "status": item.status, "ai_response": item.ai_response}
    )


@router.post("/{session_id}/supplement", response_model=Envelope[dict])
async def supplement(
    session_id: int,
    body: InputCreate,
    user: CurrentUser,
    couple: CurrentCouple,
    session: SessionDep,
) -> Envelope[dict]:
    """在 AI 回复后追加补充意见。"""
    item = await service.supplement(session, couple, user, session_id, body.content)
    return Envelope(data={"id": item.id, "status": item.status})


@router.post("/{session_id}/close", response_model=Envelope[dict])
async def close(
    session_id: int, couple: CurrentCouple, session: SessionDep
) -> Envelope[dict]:
    """关闭询问，形成共同记录。"""
    item = await service.close(session, couple, session_id)
    return Envelope(data={"id": item.id, "status": item.status})


@router.get("/{session_id}", response_model=Envelope[InquiryOut])
async def detail(
    session_id: int, user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[InquiryOut]:
    """查看详情。双方都提交之前看不到彼此的内容。"""
    return Envelope(data=await service.get_detail(session, couple, user, session_id))
