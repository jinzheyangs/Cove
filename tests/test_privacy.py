import pytest

from app.core.errors import AppError
from app.modules.couples import service as couple_service
from app.modules.diaries import service as diary_service
from app.modules.diaries.schemas import DiaryCreate
from app.modules.privacy import service as privacy_service
from app.modules.users.models import User
from tests.helpers import TEST_PASSWORD, seed_couple


async def test_unbind_requires_confirmation(session):
    a, _, couple = await seed_couple(session)

    with pytest.raises(AppError) as exc:
        await couple_service.unbind(session, couple, a, confirm=False)

    assert exc.value.code == 2008


async def test_unbind_marks_couple(session):
    a, _, couple = await seed_couple(session)

    updated = await couple_service.unbind(session, couple, a, confirm=True)

    assert updated.status == "unbound"
    assert updated.unbound_at is not None


async def test_delete_account_rejects_wrong_password(session):
    a, _, _ = await seed_couple(session)

    with pytest.raises(AppError) as exc:
        await privacy_service.delete_account(session, a, "wrong")

    assert exc.value.code == 15001


async def test_delete_account_anonymizes_and_purges(session):
    a, _, couple = await seed_couple(session)
    await diary_service.create(session, couple, a, DiaryCreate(content="我的日记"))
    a_id = a.id

    await privacy_service.delete_account(session, a, TEST_PASSWORD)

    user = await session.get(User, a_id)
    assert user is not None
    assert user.deleted_at is not None
    assert user.nickname == "已注销"
    assert user.phone == f"deleted-{a_id}"

    assert await diary_service.list_diaries(session, couple) == []


async def test_export_includes_own_content(session):
    a, _, couple = await seed_couple(session)
    await diary_service.create(session, couple, a, DiaryCreate(content="要导出的日记"))

    data = await privacy_service.export_data(session, a)

    assert data["profile"]["id"] == a.id
    assert data["diaries"][0]["content"] == "要导出的日记"
    assert data["couple"]["id"] == couple.id
