import asyncio
from uuid import uuid4

import pytest

from app.core.errors import AppError
from app.modules.coins import repository as repo
from app.modules.coins import service as coin_service
from app.modules.couples.models import Couple
from app.modules.users.models import User


async def _seed_couple(session) -> tuple[User, User, Couple]:
    a = User(phone="13800000001", password_hash="x", nickname="A")
    b = User(phone="13800000002", password_hash="x", nickname="B")
    session.add_all([a, b])
    await session.flush()
    couple = Couple(user1_id=a.id, user2_id=b.id, status="active")
    session.add(couple)
    await session.commit()
    return a, b, couple


async def _fund(session, couple: Couple, user: User, amount: int) -> None:
    """测试用：模拟系统发行，给用户充值。"""
    await repo.ensure_account(session, user.id)
    account = await repo.lock_account(session, user.id)
    assert account is not None
    account.balance += amount
    await repo.add_transaction(
        session,
        couple_id=couple.id,
        type="reward",
        from_user_id=None,
        to_user_id=user.id,
        actor_id=user.id,
        amount=amount,
        idempotency_key=f"seed-{uuid4().hex}",
    )
    await session.commit()


async def test_gift_mints_coins_to_partner(session):
    a, b, couple = await _seed_couple(session)

    tx = await coin_service.gift(session, couple, a, 30, remark="谢谢你的早餐")

    assert tx.type == "gift"
    assert tx.from_user_id is None  # 系统发行，不扣赠与方
    assert tx.to_user_id == b.id
    assert tx.actor_id == a.id
    assert await repo.get_balance(session, b.id) == 30
    assert await repo.get_balance(session, a.id) == 0


async def test_spend_deducts_and_burns(session):
    a, _, couple = await _seed_couple(session)
    await _fund(session, couple, a, 100)

    tx = await coin_service.spend(session, couple, a, 40, ref_type="secret", ref_id=1)

    assert tx.type == "consume"
    assert tx.from_user_id == a.id
    assert tx.to_user_id is None  # 销毁
    assert await repo.get_balance(session, a.id) == 60
    assert await repo.recompute_balance(session, a.id) == 60


async def test_spend_rejects_insufficient_balance(session):
    a, _, couple = await _seed_couple(session)
    await _fund(session, couple, a, 10)
    a_id = a.id

    with pytest.raises(AppError) as exc:
        await coin_service.spend(session, couple, a, 50)

    assert exc.value.code == 4001
    assert await repo.get_balance(session, a_id) == 10


async def test_same_idempotency_key_only_applies_once(session):
    a, _, couple = await _seed_couple(session)
    await _fund(session, couple, a, 100)

    first = await coin_service.spend(session, couple, a, 30, idempotency_key="k-1")
    second = await coin_service.spend(session, couple, a, 30, idempotency_key="k-1")

    assert first.id == second.id
    assert await repo.get_balance(session, a.id) == 70


async def test_reconcile_detects_mismatch(session):
    a, _, couple = await _seed_couple(session)
    await _fund(session, couple, a, 50)
    a_id = a.id

    assert await coin_service.reconcile(session) == []

    # 人为制造不一致
    account = await repo.lock_account(session, a_id)
    assert account is not None
    account.balance = 999
    await session.commit()

    assert await coin_service.reconcile(session) == [(a_id, 999, 50)]


async def test_concurrent_spend_never_goes_negative(session, session_factory):
    a, _, couple = await _seed_couple(session)
    await _fund(session, couple, a, 100)
    a_id, couple_id = a.id, couple.id

    async def attempt(key: str):
        async with session_factory() as s:
            user = await s.get(User, a_id)
            cp = await s.get(Couple, couple_id)
            return await coin_service.spend(s, cp, user, 60, idempotency_key=key)

    results = await asyncio.gather(
        attempt("k-a"), attempt("k-b"), return_exceptions=True
    )
    successes = [r for r in results if not isinstance(r, BaseException)]
    failures = [r for r in results if isinstance(r, AppError)]

    assert len(successes) == 1
    assert len(failures) == 1
    assert failures[0].code == 4001

    async with session_factory() as s:
        assert await repo.get_balance(s, a_id) == 40
        assert await repo.recompute_balance(s, a_id) == 40  # 缓存与流水一致
