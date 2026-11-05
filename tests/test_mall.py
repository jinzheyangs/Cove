import pytest

from app.core.errors import AppError
from app.modules.coins import repository as coin_repo
from app.modules.mall import service
from app.modules.mall.schemas import ItemCreate
from tests.helpers import fund_user, seed_couple


async def _listed_item(session, couple, creator, reviewer, price_coins=20):
    item = await service.create_item(
        session, couple, creator, ItemCreate(title="请你吃早餐", price_coins=price_coins)
    )
    return await service.approve_item(session, couple, reviewer, item.id)


async def test_item_starts_pending(session):
    a, _, couple = await seed_couple(session)
    item = await service.create_item(
        session, couple, a, ItemCreate(title="陪聊一小时", price_coins=15)
    )
    assert item.status == "pending"


async def test_approve_sets_price(session):
    a, b, couple = await seed_couple(session)
    item = await service.create_item(
        session, couple, a, ItemCreate(title="早餐", price_coins=20)
    )
    approved = await service.approve_item(session, couple, b, item.id, price_coins=12)

    assert approved.status == "approved"
    assert approved.approved_price == 12


async def test_buy_charges_buyer_and_creates_order(session):
    a, b, couple = await seed_couple(session)
    await fund_user(session, couple, b, 100)
    item = await _listed_item(session, couple, a, b)

    order = await service.buy(session, couple, b, item.id)

    assert order.price == 20
    assert order.status == "pending"
    assert await coin_repo.get_balance(session, b.id) == 80


async def test_cannot_buy_unapproved_item(session):
    a, b, couple = await seed_couple(session)
    await fund_user(session, couple, b, 100)
    item = await service.create_item(
        session, couple, a, ItemCreate(title="早餐", price_coins=20)
    )

    with pytest.raises(AppError) as exc:
        await service.buy(session, couple, b, item.id)

    assert exc.value.code == 7006


async def test_cannot_buy_own_item(session):
    a, b, couple = await seed_couple(session)
    await fund_user(session, couple, a, 100)
    item = await _listed_item(session, couple, a, b)

    with pytest.raises(AppError) as exc:
        await service.buy(session, couple, a, item.id)

    assert exc.value.code == 7007


async def test_creator_completes_order(session):
    a, b, couple = await seed_couple(session)
    await fund_user(session, couple, b, 100)
    item = await _listed_item(session, couple, a, b)
    order = await service.buy(session, couple, b, item.id)

    with pytest.raises(AppError) as exc:
        await service.complete_order(session, couple, b, order.id)
    assert exc.value.code == 7010

    completed = await service.complete_order(session, couple, a, order.id)
    assert completed.status == "completed"


async def test_stock_limit(session):
    a, b, couple = await seed_couple(session)
    await fund_user(session, couple, b, 100)
    item = await service.create_item(
        session,
        couple,
        a,
        ItemCreate(title="限量早餐", price_coins=20, max_orders=1),
    )
    await service.approve_item(session, couple, b, item.id)

    await service.buy(session, couple, b, item.id)

    with pytest.raises(AppError) as exc:
        await service.buy(session, couple, b, item.id)

    assert exc.value.code == 7011
    assert await coin_repo.get_balance(session, b.id) == 80
