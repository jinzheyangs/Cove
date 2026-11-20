"""绑定：新情侣的见面礼金币。

不发初始金币的话，刚配对的两个人都被 0 卡住：
批不了对方的金币申请，商城和秘密树也用不了。
"""

from sqlalchemy import select

from app.modules.coins import service as coin_service
from app.modules.coins.models import CoinTransaction
from app.modules.couples import service as couple_service
from app.modules.users.models import User
from tests.helpers import _PASSWORD_HASH


async def _two_new_users(session):
    a = User(phone="13900000001", password_hash=_PASSWORD_HASH, nickname="A")
    b = User(phone="13900000002", password_hash=_PASSWORD_HASH, nickname="B")
    session.add_all([a, b])
    await session.flush()
    return a, b


async def test_bind_gives_both_sides_welcome_coins(session):
    a, b = await _two_new_users(session)
    invite = await couple_service.create_invite(session, a)

    couple = await couple_service.bind(session, b, invite.code)

    assert await coin_service.get_balance(session, a.id) == couple_service.WELCOME_COINS
    assert await coin_service.get_balance(session, b.id) == couple_service.WELCOME_COINS

    rows = (
        await session.scalars(
            select(CoinTransaction).where(CoinTransaction.couple_id == couple.id)
        )
    ).all()
    assert len(rows) == 2
    assert {r.to_user_id for r in rows} == {a.id, b.id}
    assert all(r.type == "reward" and r.amount == couple_service.WELCOME_COINS for r in rows)
    # 系统发行：from 为空，账单上不会算成「对方给的」
    assert all(r.from_user_id is None for r in rows)


async def test_bind_is_not_charged_to_anyone(session):
    """见面礼是系统发行，不是从对方余额里扣的。"""
    a, b = await _two_new_users(session)
    invite = await couple_service.create_invite(session, a)

    await couple_service.bind(session, b, invite.code)

    rows = (
        await session.scalars(
            select(CoinTransaction).where(CoinTransaction.from_user_id.is_not(None))
        )
    ).all()
    assert rows == []
