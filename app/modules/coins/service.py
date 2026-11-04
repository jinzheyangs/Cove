"""业务层：金币规则与事务边界。

模型约定：赠与 = 系统发行（from_user_id 为 NULL），消费 = 销毁（to_user_id 为 NULL）。

`*_locked` 系列不提交事务，供其他模块把「扣币 + 业务写入」放进同一个事务。
"""

from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.coins import repository as repo
from app.modules.coins.models import CoinTransaction
from app.modules.coins.schemas import MAX_GIFT, TransactionItem
from app.modules.couples.models import Couple
from app.modules.users.models import User


async def get_balance(session: AsyncSession, user_id: int) -> int:
    return await repo.get_balance(session, user_id)


async def list_transactions(
    session: AsyncSession, user_id: int, limit: int, offset: int
) -> list[CoinTransaction]:
    return await repo.list_transactions(session, user_id, limit, offset)


async def mint_locked(
    session: AsyncSession,
    *,
    couple_id: int,
    actor_id: int,
    recipient_id: int,
    amount: int,
    tx_type: str = "gift",
    ref_type: str | None = None,
    ref_id: int | None = None,
    remark: str | None = None,
    idempotency_key: str | None = None,
) -> CoinTransaction:
    """给 recipient 发行金币。不提交事务。"""
    if amount <= 0:
        raise AppError("金币数量不合法", code=4002, status_code=400)

    await repo.ensure_account(session, recipient_id)
    account = await repo.lock_account(session, recipient_id)
    if account is None:
        raise AppError("金币账户异常", code=4003, status_code=500)
    account.balance += amount

    return await repo.add_transaction(
        session,
        couple_id=couple_id,
        type=tx_type,
        from_user_id=None,
        to_user_id=recipient_id,
        actor_id=actor_id,
        amount=amount,
        ref_type=ref_type,
        ref_id=ref_id,
        idempotency_key=idempotency_key or uuid4().hex,
        remark=remark,
    )


async def spend_locked(
    session: AsyncSession,
    *,
    couple_id: int,
    spender_id: int,
    amount: int,
    ref_type: str | None = None,
    ref_id: int | None = None,
    remark: str | None = None,
    idempotency_key: str | None = None,
) -> CoinTransaction:
    """扣减并销毁金币。不提交事务；余额不足时抛错。"""
    if amount <= 0:
        raise AppError("金币数量不合法", code=4002, status_code=400)

    await repo.ensure_account(session, spender_id)
    account = await repo.lock_account(session, spender_id)
    if account is None:
        raise AppError("金币账户异常", code=4003, status_code=500)
    if account.balance < amount:
        raise AppError("金币不足", code=4001, status_code=409)

    account.balance -= amount

    return await repo.add_transaction(
        session,
        couple_id=couple_id,
        type="consume",
        from_user_id=spender_id,
        to_user_id=None,
        actor_id=spender_id,
        amount=amount,
        ref_type=ref_type,
        ref_id=ref_id,
        idempotency_key=idempotency_key or uuid4().hex,
        remark=remark,
    )


async def gift(
    session: AsyncSession,
    couple: Couple,
    giver: User,
    amount: int,
    remark: str | None = None,
    idempotency_key: str | None = None,
) -> CoinTransaction:
    """赠与金币。金币由系统发行，不扣赠与方余额。"""
    if not 0 < amount <= MAX_GIFT:
        raise AppError("金币数量不合法", code=4002, status_code=400)

    key = idempotency_key or uuid4().hex
    existing = await repo.find_by_idempotency_key(session, key)
    if existing is not None:
        return existing

    giver_id = giver.id
    recipient_id = couple.user2_id if couple.user1_id == giver_id else couple.user1_id

    try:
        transaction = await mint_locked(
            session,
            couple_id=couple.id,
            actor_id=giver_id,
            recipient_id=recipient_id,
            amount=amount,
            remark=remark,
            idempotency_key=key,
        )
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await repo.find_by_idempotency_key(session, key)
        if existing is not None:
            return existing
        raise

    await session.refresh(transaction)
    return transaction


async def spend(
    session: AsyncSession,
    couple: Couple,
    spender: User,
    amount: int,
    *,
    ref_type: str | None = None,
    ref_id: int | None = None,
    idempotency_key: str | None = None,
    remark: str | None = None,
) -> CoinTransaction:
    """消费金币（销毁）。独立调用时使用；模块内部请用 spend_locked。"""
    if amount <= 0:
        raise AppError("金币数量不合法", code=4002, status_code=400)

    key = idempotency_key or uuid4().hex
    existing = await repo.find_by_idempotency_key(session, key)
    if existing is not None:
        return existing

    try:
        transaction = await spend_locked(
            session,
            couple_id=couple.id,
            spender_id=spender.id,
            amount=amount,
            ref_type=ref_type,
            ref_id=ref_id,
            remark=remark,
            idempotency_key=key,
        )
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await repo.find_by_idempotency_key(session, key)
        if existing is not None:
            return existing
        raise
    except AppError:
        await session.rollback()
        raise

    await session.refresh(transaction)
    return transaction


async def reconcile(session: AsyncSession) -> list[tuple[int, int, int]]:
    """从流水重算所有账户余额，返回 (user_id, 缓存余额, 应有余额) 的不一致列表。"""
    mismatches: list[tuple[int, int, int]] = []
    for account in await repo.list_accounts(session):
        expected = await repo.recompute_balance(session, account.user_id)
        if expected != account.balance:
            mismatches.append((account.user_id, account.balance, expected))
    return mismatches


def to_item(transaction: CoinTransaction, user_id: int) -> TransactionItem:
    direction = "in" if transaction.to_user_id == user_id else "out"
    return TransactionItem(
        id=transaction.id,
        type=transaction.type,
        direction=direction,
        amount=transaction.amount,
        from_user_id=transaction.from_user_id,
        to_user_id=transaction.to_user_id,
        ref_type=transaction.ref_type,
        ref_id=transaction.ref_id,
        remark=transaction.remark,
        created_at=transaction.created_at,
    )
