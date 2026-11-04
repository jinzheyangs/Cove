"""数据访问层：金币相关的所有 SQL 都在这里。"""

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.coins.models import CoinAccount, CoinTransaction


async def ensure_account(session: AsyncSession, user_id: int) -> None:
    """账户按需创建，并发安全。"""
    await session.execute(
        pg_insert(CoinAccount)
        .values(user_id=user_id, balance=0)
        .on_conflict_do_nothing(index_elements=["user_id"])
    )
    await session.flush()


async def get_balance(session: AsyncSession, user_id: int) -> int:
    value = await session.scalar(
        select(CoinAccount.balance).where(CoinAccount.user_id == user_id)
    )
    return int(value or 0)


async def lock_account(session: AsyncSession, user_id: int) -> CoinAccount | None:
    """加行锁读取账户。必须在事务内使用，且尽快提交或回滚。"""
    return await session.scalar(
        select(CoinAccount).where(CoinAccount.user_id == user_id).with_for_update()
    )


async def find_by_idempotency_key(
    session: AsyncSession, key: str
) -> CoinTransaction | None:
    return await session.scalar(
        select(CoinTransaction).where(CoinTransaction.idempotency_key == key)
    )


async def add_transaction(session: AsyncSession, **values: object) -> CoinTransaction:
    transaction = CoinTransaction(**values)
    session.add(transaction)
    await session.flush()
    return transaction


async def list_transactions(
    session: AsyncSession, user_id: int, limit: int, offset: int
) -> list[CoinTransaction]:
    stmt = (
        select(CoinTransaction)
        .where(
            or_(
                CoinTransaction.to_user_id == user_id,
                CoinTransaction.from_user_id == user_id,
                # 赠与是系统发行，from 为 NULL，靠 actor_id 让赠与方也能看到
                CoinTransaction.actor_id == user_id,
            )
        )
        .order_by(CoinTransaction.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(await session.scalars(stmt))


async def list_accounts(session: AsyncSession) -> list[CoinAccount]:
    return list(await session.scalars(select(CoinAccount)))


async def recompute_balance(session: AsyncSession, user_id: int) -> int:
    """从流水重算余额，用于对账。"""
    inflow = await session.scalar(
        select(func.coalesce(func.sum(CoinTransaction.amount), 0)).where(
            CoinTransaction.to_user_id == user_id
        )
    )
    outflow = await session.scalar(
        select(func.coalesce(func.sum(CoinTransaction.amount), 0)).where(
            CoinTransaction.from_user_id == user_id
        )
    )
    return int(inflow) - int(outflow)
