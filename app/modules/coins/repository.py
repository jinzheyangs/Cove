"""数据访问层：金币相关的所有 SQL 都在这里。

约定：不 commit。事务由 service 控制，
这样「扣币 + 业务写入」可以放进同一个事务。
"""

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.coins.models import CoinAccount, CoinTransaction


async def ensure_account(session: AsyncSession, user_id: int) -> None:
    """账户按需创建，并发安全。

    INSERT ... ON CONFLICT DO NOTHING：
    两个请求同时首次访问同一用户时，只有一个真正插入，另一个静默跳过。
    不能用「先 SELECT 再 INSERT」，那样会出现竞态。
    """
    await session.execute(
        pg_insert(CoinAccount)
        .values(user_id=user_id, balance=0)
        .on_conflict_do_nothing(index_elements=["user_id"])
    )
    await session.flush()


async def get_balance(session: AsyncSession, user_id: int) -> int:
    """读缓存余额。没有账户时返回 0，不创建账户。"""
    value = await session.scalar(
        select(CoinAccount.balance).where(CoinAccount.user_id == user_id)
    )
    return int(value or 0)


async def lock_account(session: AsyncSession, user_id: int) -> CoinAccount | None:
    """加行锁读取账户。

    SELECT ... FOR UPDATE 会阻塞其他事务对同一行的写入，
    从而把并发扣减串行化。

    必须在事务内使用，并且尽快 commit 或 rollback：
    锁持有期间不要做网络请求、调 AI、发通知。
    """
    return await session.scalar(
        select(CoinAccount).where(CoinAccount.user_id == user_id).with_for_update()
    )


async def find_by_idempotency_key(
    session: AsyncSession, key: str
) -> CoinTransaction | None:
    """按幂等键查已存在的流水。命中说明这个请求之前成功过。"""
    return await session.scalar(
        select(CoinTransaction).where(CoinTransaction.idempotency_key == key)
    )


async def add_transaction(session: AsyncSession, **values: object) -> CoinTransaction:
    """插入一条流水并 flush。幂等键冲突会抛 IntegrityError，由上层处理。"""
    transaction = CoinTransaction(**values)
    session.add(transaction)
    await session.flush()
    return transaction


async def list_transactions(
    session: AsyncSession, user_id: int, limit: int, offset: int
) -> list[CoinTransaction]:
    """列出与用户有关的流水。

    三个条件缺一不可：
    - to_user_id：别人赠给我的
    - from_user_id：我消费掉的
    - actor_id：我赠给别人的（赠与是系统发行，from 为 NULL）
    """
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


async def sum_gifts_since(session: AsyncSession, actor_id: int, since: object) -> int:
    """统计某人在 since 之后赠出的金币总额，用于每日上限。"""
    value = await session.scalar(
        select(func.coalesce(func.sum(CoinTransaction.amount), 0)).where(
            CoinTransaction.actor_id == actor_id,
            CoinTransaction.type == "gift",
            CoinTransaction.created_at >= since,
        )
    )
    return int(value or 0)


async def list_accounts(session: AsyncSession) -> list[CoinAccount]:
    """对账用：拉取全部账户。用户量大时应改成分页或只查可疑账户。"""
    return list(await session.scalars(select(CoinAccount)))


async def recompute_balance(session: AsyncSession, user_id: int) -> int:
    """从流水重算余额，用于对账。

    公式：流入总和 - 流出总和。
    这个结果和 coin_accounts.balance 不一致，就说明缓存写坏了。
    """
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
