"""秘密树：定价、扣币摘取、燃尽、销毁权限。"""

import pytest

from app.core.errors import AppError
from app.modules.coins import repository as coin_repo
from app.modules.secrets import service
from app.modules.secrets.schemas import SecretCreate
from tests.helpers import fund_user, seed_couple


async def test_publish_uses_default_cost_by_level(session):
    a, _, couple = await seed_couple(session)

    normal = await service.publish(session, couple, a, SecretCreate(content="小事"))
    deep = await service.publish(
        session, couple, a, SecretCreate(content="大事", level="deep")
    )

    assert normal.cost_coins == 10
    assert deep.cost_coins == 30


async def test_unlock_charges_and_returns_content(session):
    a, b, couple = await seed_couple(session)
    await fund_user(session, couple, b, 100)
    secret = await service.publish(
        session, couple, a, SecretCreate(content="其实我怕你走", cost_coins=20)
    )

    detail = await service.unlock(session, couple, b, secret.id)

    assert detail.content == "其实我怕你走"
    assert await coin_repo.get_balance(session, b.id) == 80


async def test_cannot_unlock_own_secret(session):
    a, _, couple = await seed_couple(session)
    secret = await service.publish(session, couple, a, SecretCreate(content="x"))

    with pytest.raises(AppError) as exc:
        await service.unlock(session, couple, a, secret.id)

    assert exc.value.code == 5002


async def test_insufficient_balance_keeps_secret_active(session):
    a, b, couple = await seed_couple(session)
    await fund_user(session, couple, b, 5)
    secret = await service.publish(
        session, couple, a, SecretCreate(content="x", cost_coins=20)
    )
    b_id = b.id

    with pytest.raises(AppError) as exc:
        await service.unlock(session, couple, b, secret.id)

    assert exc.value.code == 4001
    assert await coin_repo.get_balance(session, b_id) == 5


async def test_burn_after_read_cannot_be_reopened(session):
    a, b, couple = await seed_couple(session)
    await fund_user(session, couple, b, 100)
    secret = await service.publish(
        session,
        couple,
        a,
        SecretCreate(content="只给你看一次", cost_coins=10, is_burn_after_read=True),
    )

    first = await service.unlock(session, couple, b, secret.id)
    assert first.status == "burned"

    with pytest.raises(AppError) as exc:
        await service.unlock(session, couple, b, secret.id)
    assert exc.value.code == 5003


async def test_second_unlock_of_normal_secret_is_free(session):
    a, b, couple = await seed_couple(session)
    await fund_user(session, couple, b, 100)
    secret = await service.publish(
        session, couple, a, SecretCreate(content="可以反复看", cost_coins=20)
    )

    await service.unlock(session, couple, b, secret.id)
    await service.unlock(session, couple, b, secret.id)

    assert await coin_repo.get_balance(session, b.id) == 80


async def test_destroy_all_only_touches_my_secrets(session):
    a, b, couple = await seed_couple(session)
    mine = await service.publish(session, couple, a, SecretCreate(content="我的"))
    theirs = await service.publish(session, couple, b, SecretCreate(content="对方的"))

    count = await service.destroy_all_mine(session, couple, a)

    assert count == 1
    await session.refresh(mine)
    await session.refresh(theirs)
    assert mine.status == "destroyed"
    assert theirs.status == "active"
