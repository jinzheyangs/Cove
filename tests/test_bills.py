"""恋爱账本：金额校验、隐私过滤与统计口径。"""

from decimal import Decimal

import pytest

from app.core.errors import AppError
from app.modules.bills import service
from app.modules.bills.schemas import BillCreate
from tests.helpers import seed_couple


async def test_money_bill_requires_amount(session):
    a, _, couple = await seed_couple(session)

    with pytest.raises(AppError) as exc:
        await service.create(
            session, couple, a, BillCreate(category="吃饭", type="money", amount=None)
        )

    assert exc.value.code == 10001


async def test_non_money_bill_rejects_amount(session):
    a, _, couple = await seed_couple(session)

    with pytest.raises(AppError) as exc:
        await service.create(
            session,
            couple,
            a,
            BillCreate(category="陪伴", type="emotion", amount=Decimal("10")),
        )

    assert exc.value.code == 10002


async def test_private_bill_hidden_from_partner(session):
    a, b, couple = await seed_couple(session)
    await service.create(
        session,
        couple,
        a,
        BillCreate(amount=Decimal("50"), category="礼物", is_private=True),
    )

    assert len(await service.list_visible(session, couple, a)) == 1
    assert len(await service.list_visible(session, couple, b)) == 0


async def test_stats_aggregate_without_person_comparison(session):
    a, b, couple = await seed_couple(session)

    await service.create(
        session, couple, a, BillCreate(amount=Decimal("100"), category="吃饭", scope="shared")
    )
    await service.create(
        session,
        couple,
        a,
        BillCreate(amount=Decimal("50"), category="礼物", scope="personal", is_private=True),
    )
    await service.create(
        session, couple, b, BillCreate(amount=Decimal("30"), category="打车", scope="shared")
    )
    await service.create(
        session, couple, a, BillCreate(category="倾听", type="emotion")
    )

    stats = await service.stats(session, couple, a)
    assert stats.money_total == Decimal("180")
    assert stats.shared_total == Decimal("130")
    assert stats.personal_total == Decimal("50")
    assert stats.non_money_counts == {"emotion": 1}
    assert {c.category for c in stats.by_category} == {"吃饭", "礼物", "打车"}


async def test_stats_exclude_partners_private_bills(session):
    a, b, couple = await seed_couple(session)
    await service.create(
        session,
        couple,
        a,
        BillCreate(amount=Decimal("50"), category="礼物", is_private=True),
    )
    await service.create(
        session, couple, b, BillCreate(amount=Decimal("30"), category="打车")
    )

    stats_a = await service.stats(session, couple, a)
    stats_b = await service.stats(session, couple, b)

    assert stats_a.money_total == Decimal("80")
    assert stats_b.money_total == Decimal("30")
