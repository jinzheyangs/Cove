"""业务层：金币规则与事务边界。

模型约定：
- 赠与 = 系统发行（from_user_id 为 NULL），不扣赠与方余额
- 消费 = 销毁（to_user_id 为 NULL），金币消失而不是转给对方

为什么提供两套函数：
- `mint_locked` / `spend_locked`：只操作、不提交，
  供秘密树、商城等模块把「扣币 + 业务写入」放进同一个事务
- `gift` / `spend`：独立调用，自带幂等检查和 commit

并发安全靠三样东西：
1. SELECT ... FOR UPDATE 行锁
2. 幂等键唯一索引
3. 数据库 CHECK (balance >= 0)
"""

from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError
from app.modules.coins import repository as repo
from app.modules.coins.models import CoinTransaction
from app.modules.coins.schemas import MAX_GIFT, TransactionItem
from app.modules.couples.models import Couple
from app.modules.users.models import User


async def get_balance(session: AsyncSession, user_id: int) -> int:
    """读缓存余额。没有账户视为 0。"""
    return await repo.get_balance(session, user_id)


async def list_transactions(
    session: AsyncSession, user_id: int, limit: int, offset: int
) -> list[CoinTransaction]:
    """分页读取与用户相关的流水。"""
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
    """给 recipient 发行金币（不提交事务）。

    调用方负责 commit；如果调用方回滚，这次发行也会一起回滚。

    Args:
        actor_id: 发起人（谁给的），不等于收款人。
        recipient_id: 金币进入谁的账户。
        tx_type: gift / apply / reward 等，用于区分来源。
        idempotency_key: 不传则生成随机值，此时无法去重。
    """
    if amount <= 0:
        raise AppError("金币数量不合法", code=4002, status_code=400)

    # 先确保账户存在，再加锁。顺序不能反：
    # 账户不存在时 FOR UPDATE 会锁空，后面的加法就丢了
    await repo.ensure_account(session, recipient_id)
    account = await repo.lock_account(session, recipient_id)
    if account is None:
        raise AppError("金币账户异常", code=4003, status_code=500)
    account.balance += amount

    return await repo.add_transaction(
        session,
        couple_id=couple_id,
        type=tx_type,
        from_user_id=None,  # 系统发行
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
    """扣减并销毁金币（不提交事务）。

    余额不足时抛 AppError，不产生任何写入。
    注意：这里不回滚，由调用方决定——保持事务边界单一。
    """
    if amount <= 0:
        raise AppError("金币数量不合法", code=4002, status_code=400)

    await repo.ensure_account(session, spender_id)
    account = await repo.lock_account(session, spender_id)
    if account is None:
        raise AppError("金币账户异常", code=4003, status_code=500)

    # 判断和扣减都必须在锁内，否则两个并发请求会同时通过判断
    if account.balance < amount:
        raise AppError("金币不足", code=4001, status_code=409)

    account.balance -= amount

    return await repo.add_transaction(
        session,
        couple_id=couple_id,
        type="consume",
        from_user_id=spender_id,
        to_user_id=None,  # 销毁
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
    """赠与金币（独立接口）。

    流程：
    1. 校验金额
    2. 幂等键命中则直接返回旧流水
    3. 检查每日赠送上限
    4. 发行金币、写流水、提交

    第 2 步在检查上限之前：
    重试同一个请求不应该因为“今天已经赠满了”而失败。
    """
    if not 0 < amount <= MAX_GIFT:
        raise AppError("金币数量不合法", code=4002, status_code=400)

    key = idempotency_key or uuid4().hex
    existing = await repo.find_by_idempotency_key(session, key)
    if existing is not None:
        return existing

    # 提前取出 id，后面即使回滚也不会因为对象过期而触发隐式 IO
    giver_id = giver.id
    recipient_id = couple.user2_id if couple.user1_id == giver_id else couple.user1_id

    # 每日赠送上限，防止一个人无限发币把经济玩坏
    if settings.DAILY_GIFT_LIMIT > 0:
        # 按北京时间切天，而不是 UTC：用户感知的“今天”是本地日期
        day_start = datetime.now(ZoneInfo("Asia/Shanghai")).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        sent_today = await repo.sum_gifts_since(session, giver_id, day_start)
        if sent_today + amount > settings.DAILY_GIFT_LIMIT:
            raise AppError(
                f"今天最多赠送 {settings.DAILY_GIFT_LIMIT} 金币",
                code=4004,
                status_code=429,
            )

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
        # 并发提交同一个幂等键：唯一索引挡住了后到的那个。
        # 回滚（撤销余额加法）后返回先成功的那条流水。
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
    """消费金币（独立调用）。

    模块内部（秘密树、商城）请用 spend_locked，
    把扣币和业务写入放进同一个事务，避免“扣了钱但业务没成功”。
    """
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
        # 余额不足等业务错误：显式回滚，释放行锁
        await session.rollback()
        raise

    await session.refresh(transaction)
    return transaction


async def reconcile(session: AsyncSession) -> list[tuple[int, int, int]]:
    """从流水重算所有账户余额，返回不一致的账户。

    Returns:
        [(user_id, 缓存余额, 应有余额), ...]
        空列表表示全部一致。

    由 worker 每天调用，结果写入 Prometheus 指标并触发告警。
    """
    mismatches: list[tuple[int, int, int]] = []
    for account in await repo.list_accounts(session):
        expected = await repo.recompute_balance(session, account.user_id)
        if expected != account.balance:
            mismatches.append((account.user_id, account.balance, expected))
    return mismatches


def to_item(transaction: CoinTransaction, user_id: int) -> TransactionItem:
    """把 ORM 流水转成接口结构，并计算收支方向。

    判断依据是 to_user_id：
    钱进了我的账户就是 in，否则（消费或我发起的赠与）就是 out。
    """
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
