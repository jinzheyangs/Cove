"""站内通知：业务触发、按用户隔离、已读。"""

from app.modules.coin_applies import service as apply_service
from app.modules.notifications import service as notification_service
from app.modules.secrets import service as secret_service
from app.modules.secrets.schemas import SecretCreate
from tests.helpers import fund_user, seed_couple


async def _list(session, user_id, unread_only=False):
    return await notification_service.list_mine(
        session, user_id, unread_only=unread_only, limit=50, offset=0
    )


async def test_unlock_notifies_secret_author(session):
    a, b, couple = await seed_couple(session)
    await fund_user(session, couple, b, 100)
    secret = await secret_service.publish(
        session, couple, a, SecretCreate(content="x", cost_coins=10)
    )

    await secret_service.unlock(session, couple, b, secret.id)

    items = await _list(session, a.id)
    assert len(items) == 1
    assert items[0].type == "secret.unlocked"
    assert items[0].related_id == secret.id


async def test_notifications_are_per_user(session):
    a, b, couple = await seed_couple(session)
    await fund_user(session, couple, b, 100)
    secret = await secret_service.publish(
        session, couple, a, SecretCreate(content="x", cost_coins=10)
    )
    await secret_service.unlock(session, couple, b, secret.id)

    assert await _list(session, b.id) == []


async def test_apply_approval_notifies_applicant(session):
    a, b, couple = await seed_couple(session)
    item = await apply_service.apply(session, couple, a, 30, "陪你加班")

    await apply_service.approve(session, couple, b, item.id)

    items = await _list(session, a.id)
    assert items[0].type == "coin_apply.approved"
    assert "30" in (items[0].content or "")


async def test_mark_read_and_count(session):
    a, b, couple = await seed_couple(session)
    item = await apply_service.apply(session, couple, a, 30, "x")
    await apply_service.approve(session, couple, b, item.id)

    assert await notification_service.unread_count(session, a.id) == 1

    items = await _list(session, a.id)
    await notification_service.mark_read(session, a.id, items[0].id)
    assert await notification_service.unread_count(session, a.id) == 0

    second = await apply_service.apply(session, couple, a, 10, "再一次")
    await apply_service.reject(session, couple, b, second.id)

    assert await notification_service.mark_all_read(session, a.id) == 1
