"""商城：上架即生效（无需审批）、购买扣币、库存与核销权限。"""

import pytest

from app.core.errors import AppError
from app.modules.coins import repository as coin_repo
from app.modules.mall import service
from app.modules.mall.schemas import ItemCreate
from tests.helpers import fund_user, seed_couple


async def _listed_item(session, couple, creator, price_coins=20):
    # 上架无需审批：create_item 返回的商品已经是 approved
    return await service.create_item(
        session, couple, creator, ItemCreate(title="请你吃早餐", price_coins=price_coins)
    )


async def test_item_is_approved_on_create(session):
    a, _, couple = await seed_couple(session)
    item = await service.create_item(
        session, couple, a, ItemCreate(title="陪聊一小时", price_coins=15)
    )
    assert item.status == "approved"


async def test_edit_price_takes_effect(session):
    a, b, couple = await seed_couple(session)
    item = await service.create_item(
        session, couple, a, ItemCreate(title="早餐", price_coins=20)
    )
    edited = await service.edit_item(
        session, couple, a, item.id, ItemCreate(title="早餐", price_coins=12)
    )

    assert edited.status == "approved"
    assert edited.price_coins == 12


async def test_edit_by_other_is_rejected(session):
    a, b, couple = await seed_couple(session)
    item = await service.create_item(
        session, couple, a, ItemCreate(title="早餐", price_coins=20)
    )

    with pytest.raises(AppError) as exc:
        await service.edit_item(
            session, couple, b, item.id, ItemCreate(title="早餐", price_coins=1)
        )

    assert exc.value.code == 7004


async def test_buy_charges_buyer_and_creates_order(session):
    a, b, couple = await seed_couple(session)
    await fund_user(session, couple, b, 100)
    item = await _listed_item(session, couple, a)

    order = await service.buy(session, couple, b, item.id)

    assert order.price == 20
    assert order.status == "pending"
    assert await coin_repo.get_balance(session, b.id) == 80


async def test_cannot_buy_offline_item(session):
    a, b, couple = await seed_couple(session)
    await fund_user(session, couple, b, 100)
    item = await service.create_item(
        session, couple, a, ItemCreate(title="早餐", price_coins=20)
    )
    await service.offline_item(session, couple, a, item.id)

    with pytest.raises(AppError) as exc:
        await service.buy(session, couple, b, item.id)

    assert exc.value.code == 7006


async def test_cannot_buy_own_item(session):
    a, b, couple = await seed_couple(session)
    await fund_user(session, couple, a, 100)
    item = await _listed_item(session, couple, a)

    with pytest.raises(AppError) as exc:
        await service.buy(session, couple, a, item.id)

    assert exc.value.code == 7007


async def test_creator_completes_order(session):
    a, b, couple = await seed_couple(session)
    await fund_user(session, couple, b, 100)
    item = await _listed_item(session, couple, a)
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

    await service.buy(session, couple, b, item.id)

    with pytest.raises(AppError) as exc:
        await service.buy(session, couple, b, item.id)

    assert exc.value.code == 7011
    assert await coin_repo.get_balance(session, b.id) == 80
