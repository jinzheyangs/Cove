"""日记：各自视角关联、权限与字段回读。"""

import pytest

from app.core.errors import AppError
from app.modules.diaries import service
from app.modules.diaries.schemas import DiaryCreate, DiaryUpdate
from tests.helpers import seed_couple


async def test_two_perspectives_share_event_id(session):
    a, b, couple = await seed_couple(session)
    event_id = "event-001"

    await service.create(
        session, couple, a, DiaryCreate(content="我觉得那天很开心", event_id=event_id)
    )
    await service.create(
        session, couple, b, DiaryCreate(content="我其实有点累", event_id=event_id)
    )

    items = await service.list_diaries(session, couple, event_id=event_id)
    assert len(items) == 2
    assert {i.content for i in items} == {"我觉得那天很开心", "我其实有点累"}


async def test_cannot_edit_partners_personal_diary(session):
    a, b, couple = await seed_couple(session)
    diary = await service.create(session, couple, a, DiaryCreate(content="我的秘密心情"))

    with pytest.raises(AppError) as exc:
        await service.update(session, couple, b, diary.id, DiaryUpdate(content="改了"))

    assert exc.value.code == 8002


async def test_shared_diary_editable_by_both(session):
    a, b, couple = await seed_couple(session)
    diary = await service.create(
        session, couple, a, DiaryCreate(mode="shared", content="初稿")
    )

    updated = await service.update(session, couple, b, diary.id, DiaryUpdate(content="一起改完"))

    assert updated.content == "一起改完"


async def test_mood_tags_and_location_roundtrip(session):
    a, _, couple = await seed_couple(session)
    diary = await service.create(
        session,
        couple,
        a,
        DiaryCreate(
            content="下雨天",
            mood_tags=["平静", "想他"],
            location="杭州西湖",
            images=["https://example.com/1.jpg"],
        ),
    )

    assert diary.mood_tags == ["平静", "想他"]
    assert diary.location == "杭州西湖"
    assert diary.images == ["https://example.com/1.jpg"]
