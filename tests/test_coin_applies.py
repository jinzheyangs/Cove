import pytest

from app.core.errors import AppError
from app.modules.coin_applies import service
from app.modules.coins import repository as coin_repo
from tests.helpers import seed_couple


async def test_apply_is_pending(session):
    a, _, couple = await seed_couple(session)
    item = await service.apply(session, couple, a, 30, "昨晚陪你聊到很晚")

    assert item.status == "pending"
    assert item.approved_amount is None


async def test_approve_mints_coins_to_applicant(session):
    a, b, couple = await seed_couple(session)
    item = await service.apply(session, couple, a, 40, "陪你看病")

    approved = await service.approve(session, couple, b, item.id)

    assert approved.status == "approved"
    assert approved.approved_amount == 40
    assert await coin_repo.get_balance(session, a.id) == 40


async def test_approve_can_adjust_amount(session):
    a, b, couple = await seed_couple(session)
    item = await service.apply(session, couple, a, 100, "做了很多事")

    approved = await service.approve(session, couple, b, item.id, amount=30)

    assert approved.approved_amount == 30
    assert await coin_repo.get_balance(session, a.id) == 30


async def test_cannot_approve_own_application(session):
    a, _, couple = await seed_couple(session)
    item = await service.apply(session, couple, a, 30, "x")

    with pytest.raises(AppError) as exc:
        await service.approve(session, couple, a, item.id)

    assert exc.value.code == 6003


async def test_reject_gives_no_coins(session):
    a, b, couple = await seed_couple(session)
    item = await service.apply(session, couple, a, 30, "x")

    rejected = await service.reject(session, couple, b, item.id, "下次吧")

    assert rejected.status == "rejected"
    assert await coin_repo.get_balance(session, a.id) == 0
