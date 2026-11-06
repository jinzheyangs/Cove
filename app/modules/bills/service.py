"""业务层：恋爱账本与统计。

统计刻意不输出「谁付了多少」，只给共同视角的汇总。
"""

from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.bills import repository as repo
from app.modules.bills.models import Bill
from app.modules.bills.schemas import BillCreate, BillStats, CategoryStat
from app.modules.couples.models import Couple
from app.modules.users.models import User

_ZERO = Decimal("0")


async def create(
    session: AsyncSession, couple: Couple, payer: User, body: BillCreate
) -> Bill:
    """新增账目。

    两条互斥规则：
    - 金钱支出必须有金额
    - 非金钱付出不能有金额（不把陪伴和情绪劳动数字化）
    """
    if body.type == "money":
        if body.amount is None or body.amount <= 0:
            raise AppError("金额类支出必须填写金额", code=10001, status_code=400)
    elif body.amount:
        raise AppError("非金钱付出不需要填写金额", code=10002, status_code=400)

    key = body.idempotency_key
    if key:
        existing = await repo.get_by_idempotency_key(session, couple.id, key)
        if existing is not None:
            return existing

    try:
        bill = await repo.create(
            session,
            couple_id=couple.id,
            payer_id=payer.id,
            amount=body.amount,
            category=body.category,
            type=body.type,
            scope=body.scope,
            is_private=body.is_private,
            remark=body.remark,
            idempotency_key=key,
        )
        await session.commit()
    except IntegrityError:
        await session.rollback()
        if key:
            existing = await repo.get_by_idempotency_key(session, couple.id, key)
            if existing is not None:
                return existing
        raise

    await session.refresh(bill)
    return bill


async def list_visible(
    session: AsyncSession,
    couple: Couple,
    viewer: User,
    *,
    bill_type: str | None = None,
    scope: str | None = None,
) -> list[Bill]:
    """列出当前用户可见的账目。"""
    return await repo.list_visible(
        session, couple.id, viewer.id, bill_type=bill_type, scope=scope
    )


async def _get_own(session: AsyncSession, couple: Couple, user: User, bill_id: int) -> Bill:
    """取出自己记的账。

    只能改/删自己记的，避免篡改对方的数据。
    """
    bill = await repo.get(session, bill_id)
    if bill is None or bill.couple_id != couple.id:
        raise AppError("记录不存在", code=10003, status_code=404)
    if bill.payer_id != user.id:
        raise AppError("只能修改自己记的账", code=10004, status_code=403)
    return bill


async def update(
    session: AsyncSession, couple: Couple, user: User, bill_id: int, body: BillCreate
) -> Bill:
    """整体更新一条账目（不是部分更新）。"""
    bill = await _get_own(session, couple, user, bill_id)
    bill.amount = body.amount
    bill.category = body.category
    bill.type = body.type
    bill.scope = body.scope
    bill.is_private = body.is_private
    bill.remark = body.remark
    await session.commit()
    await session.refresh(bill)
    return bill


async def delete(session: AsyncSession, couple: Couple, user: User, bill_id: int) -> None:
    """删除自己记的账。"""
    bill = await _get_own(session, couple, user, bill_id)
    await repo.delete(session, bill)
    await session.commit()


async def stats(session: AsyncSession, couple: Couple, viewer: User) -> BillStats:
    """汇总统计。

    在 Python 里聚合是为了代码直观；数据量大了可以改成 SQL 聚合。
    更重要的是：返回结构里没有「个人占比」，
    避免这个功能变成谁付出更多的比较工具。
    """
    bills = await repo.list_visible(session, couple.id, viewer.id)

    money_total = _ZERO
    shared_total = _ZERO
    personal_total = _ZERO
    by_category: dict[str, Decimal] = {}
    non_money: dict[str, int] = {}

    for bill in bills:
        if bill.type == "money":
            amount = bill.amount or _ZERO
            money_total += amount
            if bill.scope == "shared":
                shared_total += amount
            else:
                personal_total += amount
            by_category[bill.category] = by_category.get(bill.category, _ZERO) + amount
        else:
            # 非金钱付出只计数，不求和
            non_money[bill.type] = non_money.get(bill.type, 0) + 1

    return BillStats(
        count=len(bills),
        money_total=money_total,
        shared_total=shared_total,
        personal_total=personal_total,
        by_category=[
            CategoryStat(category=c, total=t)
            # 按金额从大到小，前端直接照着渲染
            for c, t in sorted(by_category.items(), key=lambda item: item[1], reverse=True)
        ],
        non_money_counts=non_money,
    )
