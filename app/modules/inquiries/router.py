from fastapi import APIRouter

from app.core.deps import CurrentUser, SessionDep
from app.core.schemas import Envelope
from app.modules.couples.deps import CurrentCouple
from app.modules.inquiries import service
from app.modules.inquiries.schemas import InquiryCreate, InquiryOut, InputCreate

router = APIRouter(prefix="/inquiries", tags=["inquiries"])


@router.post("", response_model=Envelope[dict])
async def create(
    body: InquiryCreate, couple: CurrentCouple, session: SessionDep
) -> Envelope[dict]:
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
    item = await service.submit_input(session, couple, user, session_id, body.content)
    return Envelope(data={"id": item.id, "status": item.status})


@router.post("/{session_id}/generate", response_model=Envelope[dict])
async def generate(
    session_id: int, couple: CurrentCouple, session: SessionDep
) -> Envelope[dict]:
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
    item = await service.supplement(session, couple, user, session_id, body.content)
    return Envelope(data={"id": item.id, "status": item.status})


@router.post("/{session_id}/close", response_model=Envelope[dict])
async def close(
    session_id: int, couple: CurrentCouple, session: SessionDep
) -> Envelope[dict]:
    item = await service.close(session, couple, session_id)
    return Envelope(data={"id": item.id, "status": item.status})


@router.get("/{session_id}", response_model=Envelope[InquiryOut])
async def detail(
    session_id: int, user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[InquiryOut]:
    return Envelope(data=await service.get_detail(session, couple, user, session_id))
