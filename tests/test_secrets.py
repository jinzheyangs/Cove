"""秘密树：定价、扣币摘取、读完即销毁、销毁权限。"""

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


async def test_read_once_then_destroyed(session):
    """读完即销毁：正文只在这一次响应里给出，库里内容清空，不可能再读第二次。"""
    a, b, couple = await seed_couple(session)
    await fund_user(session, couple, b, 100)
    secret = await service.publish(
        session, couple, a, SecretCreate(content="只给你看一次", cost_coins=10)
    )
    secret_id = secret.id

    first = await service.unlock(session, couple, b, secret_id)
    assert first.status == "destroyed"
    assert first.content == "只给你看一次"
    assert await coin_repo.get_balance(session, b.id) == 90

    await session.refresh(secret)
    assert secret.status == "destroyed"
    assert secret.content == ""   # 正文已抹掉

    with pytest.raises(AppError) as exc:
        await service.unlock(session, couple, b, secret_id)
    assert exc.value.code == 5003

    # 第二次被拒时不能再扣币
    assert await coin_repo.get_balance(session, b.id) == 90
