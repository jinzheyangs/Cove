"""业务层：金币申请的提交与审批。

审批通过时，状态变更、金币发行、通知写入在同一个事务里：
要么都成功，要么都回滚，不会出现“状态变了但钱没到”。
"""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.coin_applies import repository as repo
from app.modules.coin_applies.models import CoinApply
from app.modules.coins import service as coin_service
from app.modules.couples.models import Couple
from app.modules.notifications import service as notification_service
from app.modules.users.models import User

# 同时最多允许多少条待审批，防止一个人刷屏
MAX_PENDING = 5


def _partner_id(couple: Couple, user_id: int) -> int:
    """关系里的另一个人。couples 表保证只有两个成员。"""
    return couple.user2_id if couple.user1_id == user_id else couple.user1_id


async def apply(
    session: AsyncSession, couple: Couple, applicant: User, amount: int, reason: str
) -> CoinApply:
    """提交一条金币申请。

    只是登记，不发钱；等对方审批后才由通知逻辑触发发行。
    """
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
    """我发起的全部申请，包含已通过和已拒绝。"""
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
    """审批前的统一校验。

    一次性检查四件事：
    - 申请存在，且属于当前关系（防越权）
    - 不是自己审批自己
    - 状态仍是 pending（防重复审批）
    - 已加行锁（防并发双发）
    """
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
    """通过申请并发放金币。

    amount 为空时按申请金额发放；否则以审批人填的为准。
    发行、状态更新、通知都在这一个事务里。
    """
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
        item.decided_at = datetime.now(UTC)
        await notification_service.notify(
            session,
            user_id=item.applicant_id,
            type="coin_apply.approved",
            title="你的金币申请通过了",
            content=f"获得 {final_amount} 金币",
            related_type="coin_apply",
            related_id=item.id,
        )
        await session.commit()
    except AppError:
        # 金币账户异常等业务错误：整体回滚，释放行锁
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
    """拒绝申请。不发放金币，只更新状态并通知申请人。"""
    item = await _get_pending_for_review(session, couple, reviewer, apply_id)
    item.status = "rejected"
    item.decided_by = reviewer.id
    item.decision_remark = remark
    item.decided_at = datetime.now(UTC)
    await notification_service.notify(
        session,
        user_id=item.applicant_id,
        type="coin_apply.rejected",
        title="你的金币申请被拒绝了",
        content=remark,
        related_type="coin_apply",
        related_id=item.id,
    )
    await session.commit()
    await session.refresh(item)
    return item
