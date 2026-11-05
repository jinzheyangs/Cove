from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.modules.coins import repository as coin_repo
from app.modules.couples.models import Couple
from app.modules.users.models import User

TEST_PASSWORD = "pass1234"
# 只算一次，避免每个测试都做 argon2
_PASSWORD_HASH = hash_password(TEST_PASSWORD)


async def seed_couple(
    session: AsyncSession, phone_a: str = "13800000001", phone_b: str = "13800000002"
) -> tuple[User, User, Couple]:
    a = User(phone=phone_a, password_hash=_PASSWORD_HASH, nickname="A")
    b = User(phone=phone_b, password_hash=_PASSWORD_HASH, nickname="B")
    session.add_all([a, b])
    await session.flush()
    couple = Couple(
        user1_id=min(a.id, b.id),
        user2_id=max(a.id, b.id),
        status="active",
    )
    session.add(couple)
    await session.commit()
    return a, b, couple


async def fund_user(
    session: AsyncSession, couple: Couple, user: User, amount: int
) -> None:
    """测试用：模拟系统发行，给用户充值。"""
    await coin_repo.ensure_account(session, user.id)
    account = await coin_repo.lock_account(session, user.id)
    assert account is not None
    account.balance += amount
    await coin_repo.add_transaction(
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
