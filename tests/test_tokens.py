"""令牌：签发、轮换、登出与过期拒绝。"""

import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from app.core.errors import AppError
from app.modules.users import repository as user_repo
from app.modules.users import service
from tests.helpers import seed_couple


async def test_issue_tokens_returns_both(session):
    a, _, _ = await seed_couple(session)

    access, refresh = await service.issue_tokens(session, a)

    assert access
    assert refresh


async def test_refresh_rotates_and_old_token_dies(session):
    a, _, _ = await seed_couple(session)
    _, refresh = await service.issue_tokens(session, a)

    _, new_refresh, user = await service.refresh_tokens(session, refresh)

    assert new_refresh != refresh
    assert user.id == a.id

    with pytest.raises(AppError) as exc:
        await service.refresh_tokens(session, refresh)
    assert exc.value.code == 1005


async def test_logout_revokes_token(session):
    a, _, _ = await seed_couple(session)
    _, refresh = await service.issue_tokens(session, a)

    await service.logout(session, refresh)

    with pytest.raises(AppError):
        await service.refresh_tokens(session, refresh)


async def test_logout_all_revokes_every_session(session):
    a, _, _ = await seed_couple(session)
    await service.issue_tokens(session, a)
    await service.issue_tokens(session, a)

    count = await service.logout_all(session, a)

    assert count >= 2


async def test_expired_refresh_is_rejected(session):
    a, _, _ = await seed_couple(session)
    raw = "expired-refresh-token"
    await user_repo.create_refresh_token(
        session,
        user_id=a.id,
        token_hash=hashlib.sha256(raw.encode()).hexdigest(),
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    await session.commit()

    with pytest.raises(AppError) as exc:
        await service.refresh_tokens(session, raw)

    assert exc.value.code == 1005
