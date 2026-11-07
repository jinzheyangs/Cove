"""纪念日倒计时：在一起、生日、自定义、闰年与一次性事件。"""

from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from app.core.errors import AppError
from app.modules.anniversaries import service
from app.modules.anniversaries.models import Anniversary
from app.modules.anniversaries.schemas import (
    AnniversaryCreate,
    AnniversaryUpdate,
)
from app.modules.users import service as user_service
from app.modules.users.schemas import ProfileUpdate
from tests.helpers import seed_couple

DAY = date(2026, 11, 7)


def test_next_occurrence_handles_leap_day():
    anchor = date(2000, 2, 29)

    assert service.next_occurrence(anchor, date(2026, 2, 27), True) == date(
        2026, 2, 28
    )
    assert service.next_occurrence(anchor, date(2026, 2, 28), True) == date(
        2026, 2, 28
    )
    assert service.next_occurrence(anchor, date(2026, 3, 1), True) == date(
        2027, 2, 28
    )


def test_next_occurrence_keeps_future_anchor():
    anchor = date(2028, 1, 1)

    assert service.next_occurrence(anchor, DAY, True) == anchor


async def test_list_includes_relationship_birthday_and_custom(session):
    a, b, couple = await seed_couple(session)
    couple.bind_at = datetime(2025, 11, 1, tzinfo=UTC)
    a.birthday = date(1998, 5, 20)
    b.birthday = date(2000, 10, 1)
    await session.commit()

    await service.create(
        session,
        couple,
        a,
        AnniversaryCreate(
            title="第一次旅行", date=date(2024, 6, 1), repeat_yearly=True
        ),
        day=DAY,
    )
    await service.create(
        session,
        couple,
        b,
        AnniversaryCreate(
            title="领证", date=date(2027, 1, 1), repeat_yearly=False
        ),
        day=DAY,
    )

    entries = await service.list_entries(session, couple, day=DAY)
    by_title = {entry.title: entry for entry in entries}

    assert by_title["在一起"].days_left == 359
    assert by_title["在一起"].years == 2
    assert by_title["A的生日"].days_left == 194
    assert by_title["A的生日"].years == 29
    assert by_title["B的生日"].days_left == 328
    assert by_title["第一次旅行"].days_left == 206
    assert by_title["领证"].days_left == 55
    assert by_title["领证"].years is None

    # 未来的排前面，最近的在最前
    assert [entry.title for entry in entries] == [
        "领证",
        "A的生日",
        "第一次旅行",
        "B的生日",
        "在一起",
    ]


async def test_create_is_idempotent(session):
    a, _, couple = await seed_couple(session)
    body = AnniversaryCreate(
        title="第一次旅行",
        date=date(2024, 6, 1),
        idempotency_key="anniv-1",
    )

    first = await service.create(session, couple, a, body, day=DAY)
    second = await service.create(session, couple, a, body, day=DAY)

    assert first.id == second.id
    assert await session.scalar(select(func.count()).select_from(Anniversary)) == 1


async def test_partner_can_update_and_delete_custom(session):
    a, b, couple = await seed_couple(session)
    created = await service.create(
        session,
        couple,
        a,
        AnniversaryCreate(title="第一次旅行", date=date(2024, 6, 1)),
        day=DAY,
    )

    updated = await service.update(
        session,
        couple,
        created.id,
        AnniversaryUpdate(title="第一次一起出远门", date=date(2024, 6, 2)),
        day=DAY,
    )
    assert updated.title == "第一次一起出远门"
    assert updated.date == date(2024, 6, 2)

    await service.delete(session, couple, created.id)
    assert await session.scalar(select(func.count()).select_from(Anniversary)) == 0


async def test_one_off_past_event_is_marked_passed(session):
    a, _, couple = await seed_couple(session)
    await service.create(
        session,
        couple,
        a,
        AnniversaryCreate(
            title="看演唱会", date=date(2026, 10, 1), repeat_yearly=False
        ),
        day=DAY,
    )

    entries = await service.list_entries(session, couple, day=DAY)
    event = next(entry for entry in entries if entry.title == "看演唱会")

    assert event.passed is True
    assert event.days_left == -37
    assert event.years is None


async def test_unknown_anniversary_returns_404(session):
    _, _, couple = await seed_couple(session)

    with pytest.raises(AppError) as exc:
        await service.update(
            session, couple, 99999, AnniversaryUpdate(title="不存在")
        )

    assert exc.value.code == 18001


async def test_birthday_lives_on_profile(session):
    a, _, _ = await seed_couple(session)

    updated = await user_service.update_profile(
        session, a, ProfileUpdate(birthday=date(2000, 1, 2))
    )
    assert updated.birthday == date(2000, 1, 2)
    assert user_service.to_out(updated).birthday == date(2000, 1, 2)

    cleared = await user_service.update_profile(
        session, updated, ProfileUpdate(birthday=None)
    )
    assert cleared.birthday is None


def test_birthday_rejects_future_date():
    with pytest.raises(ValidationError):
        ProfileUpdate(birthday=date(2999, 1, 1))
