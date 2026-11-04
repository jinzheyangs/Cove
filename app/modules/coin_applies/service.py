"""业务层：金币申请的提交与审批。"""

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.coin_applies import repository as repo
from app.modules.coin_applies.models import CoinApply
from app.modules.coins import service as coin_service
from app.modules.couples.models import Couple
from app.modules.users.models import User

MAX_PENDING = 5


def _partner_id(couple: Couple, user_id: int) -> int:
    return couple.user2_id if couple.user1_id == user_id else couple.user1_id


async def apply(
    session: AsyncSession, couple: Couple, applicant: User, amount: int, reason: str
) -> CoinApply:
    if await repo.count_pending(session, applicant.id) >= MAX_PENDING:
        raise AppError("待审批的申请太多了", code=6001, status_code=409)

    item = await repo.create(
        session,
        couple_id=couple.id,
        applicant_id=applicant.id,
        amount=amount,
        reason=reason,
    )
    await session.commit()
    await session.refresh(item)
    return item


async def list_mine(session: AsyncSession, user: User) -> list[CoinApply]:
    return await repo.list_by_applicant(session, user.id)


async def list_pending_for_me(
    session: AsyncSession, couple: Couple, user: User
) -> list[CoinApply]:
    """对方发起的、等我审批的申请。"""
    return await repo.list_pending_by_applicant(
        session, couple.id, _partner_id(couple, user.id)
    )


async def _get_pending_for_review(
    session: AsyncSession, couple: Couple, reviewer: User, apply_id: int
) -> CoinApply:
    item = await repo.get_for_update(session, apply_id)
    if item is None or item.couple_id != couple.id:
        raise AppError("申请不存在", code=6002, status_code=404)
    if item.applicant_id == reviewer.id:
        raise AppError("不能审批自己的申请", code=6003, status_code=403)
    if item.status != "pending":
        raise AppError("这条申请已经处理过了", code=6004, status_code=409)
    return item


async def approve(
    session: AsyncSession,
    couple: Couple,
    reviewer: User,
    apply_id: int,
    amount: int | None = None,
    remark: str | None = None,
) -> CoinApply:
    item = await _get_pending_for_review(session, couple, reviewer, apply_id)
    final_amount = amount or item.amount

    try:
        await coin_service.mint_locked(
            session,
            couple_id=couple.id,
            actor_id=reviewer.id,
            recipient_id=item.applicant_id,
            amount=final_amount,
            tx_type="apply",
            ref_type="coin_apply",
            ref_id=item.id,
            remark=remark,
        )
        item.status = "approved"
        item.approved_amount = final_amount
        item.decided_by = reviewer.id
        item.decision_remark = remark
        item.decided_at = datetime.now(timezone.utc)
        await session.commit()
    except AppError:
        await session.rollback()
        raise

    await session.refresh(item)
    return item


async def reject(
    session: AsyncSession,
    couple: Couple,
    reviewer: User,
    apply_id: int,
    remark: str | None = None,
) -> CoinApply:
    item = await _get_pending_for_review(session, couple, reviewer, apply_id)
    item.status = "rejected"
    item.decided_by = reviewer.id
    item.decision_remark = remark
    item.decided_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(item)
    return item
