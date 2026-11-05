"""恋爱账本的 HTTP 接口。

所有读取接口都会自动过滤掉对方的隐私支出。
"""

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, SessionDep
from app.core.schemas import Envelope
from app.modules.bills import service
from app.modules.bills.schemas import BillCreate, BillOut, BillStats
from app.modules.couples.deps import CurrentCouple

router = APIRouter(prefix="/bills", tags=["bills"])


@router.post("", response_model=Envelope[BillOut])
async def create(
    body: BillCreate, user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[BillOut]:
    """记一笔支出或付出。"""
    bill = await service.create(session, couple, user, body)
    return Envelope(data=BillOut.model_validate(bill))


@router.get("", response_model=Envelope[list[BillOut]])
async def list_bills(
    user: CurrentUser,
    couple: CurrentCouple,
    session: SessionDep,
    type: Annotated[
        str | None, Query(pattern="^(money|time|energy|emotion)$")
    ] = None,
    scope: Annotated[str | None, Query(pattern="^(shared|personal)$")] = None,
) -> Envelope[list[BillOut]]:
    """列出可见账目，可按类型和共同/个人过滤。"""
    bills = await service.list_visible(
        session, couple, user, bill_type=type, scope=scope
    )
    return Envelope(data=[BillOut.model_validate(b) for b in bills])


@router.get("/stats", response_model=Envelope[BillStats])
async def stats(
    user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[BillStats]:
    """统计汇总。只给共同视角，不提供个人对比。"""
    return Envelope(data=await service.stats(session, couple, user))


@router.put("/{bill_id}", response_model=Envelope[BillOut])
async def update(
    bill_id: int,
    body: BillCreate,
    user: CurrentUser,
    couple: CurrentCouple,
    session: SessionDep,
) -> Envelope[BillOut]:
    """更新自己记的账。"""
    bill = await service.update(session, couple, user, bill_id, body)
    return Envelope(data=BillOut.model_validate(bill))


@router.delete("/{bill_id}", response_model=Envelope[None])
async def delete(
    bill_id: int, user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[None]:
    """删除自己记的账。"""
    await service.delete(session, couple, user, bill_id)
    return Envelope()
