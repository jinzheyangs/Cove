"""日记：各自视角关联、权限与字段回读。"""

import pytest

from app.core.errors import AppError
from app.core.storage import LocalStorage
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


def _fake_storage(tmp_path):
    return LocalStorage(tmp_path)


async def test_delete_diary_removes_its_image_file(session, tmp_path, monkeypatch):
    storage = _fake_storage(tmp_path)
    key = "couples/1/diaries/1/leaf.png"
    storage.save(key, b"leaf", "image/png")
    monkeypatch.setattr(service, "get_storage", lambda: storage)

    a, _, couple = await seed_couple(session)
    diary = await service.create(session, couple, a, DiaryCreate(images=[key]))
    assert (tmp_path / key).exists()

    await service.delete(session, couple, a, diary.id)

    assert not (tmp_path / key).exists()


async def test_image_kept_while_another_diary_still_uses_it(session, tmp_path, monkeypatch):
    storage = _fake_storage(tmp_path)
    key = "couples/1/diaries/1/shared.png"
    storage.save(key, b"shared", "image/png")
    monkeypatch.setattr(service, "get_storage", lambda: storage)

    a, _, couple = await seed_couple(session)
    first = await service.create(session, couple, a, DiaryCreate(images=[key]))
    second = await service.create(session, couple, a, DiaryCreate(images=[key]))

    await service.delete(session, couple, a, first.id)

    assert (tmp_path / key).exists()
    assert second.images == [key]


async def test_title_alone_is_enough(session):
    """只写主题也能存：心得和照片允许随后补。

    前端把主题设成必填项，后端必须跟着一起认主题，
    否则会出现「按钮是亮的、点了却报『写点什么』」的错位。
    """
    a, _, couple = await seed_couple(session)
    diary = await service.create(session, couple, a, DiaryCreate(title="早市的柿子"))

    assert diary.title == "早市的柿子"
    assert (diary.content or "") == ""
    assert diary.images == []


async def test_all_three_empty_is_still_rejected(session):
    a, _, couple = await seed_couple(session)
    with pytest.raises(AppError) as exc:
        await service.create(
            session, couple, a, DiaryCreate(title="   ", content="  ", images=[])
        )
    assert exc.value.code == 8004


async def test_update_can_clear_note_when_title_remains(session):
    """心得清空、只留主题不算空记录。"""
    a, _, couple = await seed_couple(session)
    diary = await service.create(
        session, couple, a, DiaryCreate(title="早市的柿子", content="摊主多塞了两个")
    )

    updated = await service.update(session, couple, a, diary.id, DiaryUpdate(content=""))

    assert updated.content == ""
    assert updated.title == "早市的柿子"


async def test_update_dropping_image_removes_only_the_dropped_one(session, tmp_path, monkeypatch):
    storage = _fake_storage(tmp_path)
    keep = "couples/1/diaries/1/keep.png"
    drop = "couples/1/diaries/1/drop.png"
    storage.save(keep, b"keep", "image/png")
    storage.save(drop, b"drop", "image/png")
    monkeypatch.setattr(service, "get_storage", lambda: storage)

    a, _, couple = await seed_couple(session)
    diary = await service.create(
        session, couple, a, DiaryCreate(content="两张图", images=[keep, drop])
    )

    await service.update(session, couple, a, diary.id, DiaryUpdate(images=[keep]))

    assert (tmp_path / keep).exists()
    assert not (tmp_path / drop).exists()
