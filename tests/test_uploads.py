"""图片上传：类型/大小校验、本地存储、删除归属、日记 URL 映射。"""

import pytest

from app.core.config import settings
from app.core.errors import AppError
from app.core.storage import LocalStorage
from app.modules.diaries import service as diary_service
from app.modules.diaries.schemas import DiaryCreate
from app.modules.uploads import service as upload_service
from tests.helpers import seed_couple

# 最小 PNG 文件头，服务只校验魔数，不解析完整图片
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 32


@pytest.fixture
def local_storage(tmp_path, monkeypatch):
    """把存储单例替换成临时目录，避免测试污染 ./uploads。"""
    from app.core import storage as storage_module

    store = LocalStorage(tmp_path, "/uploads")
    monkeypatch.setattr(storage_module, "_storage", store)
    return store


async def test_upload_png_writes_file_and_returns_key(session, local_storage):
    _, _, couple = await seed_couple(session)

    result = await upload_service.upload_diary_image(couple, "image/png", PNG_BYTES)

    assert result.key.startswith(f"couples/{couple.id}/diaries/")
    assert result.key.endswith(".png")
    assert result.url == f"/uploads/{result.key}"
    assert (local_storage.root / result.key).exists()


async def test_upload_rejects_unsupported_type(session, local_storage):
    _, _, couple = await seed_couple(session)

    with pytest.raises(AppError) as exc:
        await upload_service.upload_diary_image(couple, "text/plain", b"hello")

    assert exc.value.code == 16001


async def test_upload_rejects_magic_mismatch(session, local_storage):
    _, _, couple = await seed_couple(session)

    with pytest.raises(AppError) as exc:
        await upload_service.upload_diary_image(couple, "image/png", b"not a png")

    assert exc.value.code == 16001


async def test_upload_rejects_too_large(session, local_storage, monkeypatch):
    _, _, couple = await seed_couple(session)
    monkeypatch.setattr(settings, "UPLOAD_MAX_BYTES", 10)

    with pytest.raises(AppError) as exc:
        await upload_service.upload_diary_image(
            couple, "image/png", PNG_BYTES + b"x" * 20
        )

    assert exc.value.code == 16002


async def test_delete_removes_own_file(session, local_storage):
    _, _, couple = await seed_couple(session)
    result = await upload_service.upload_diary_image(couple, "image/png", PNG_BYTES)

    await upload_service.delete_upload(couple, result.key)

    assert not (local_storage.root / result.key).exists()


async def test_cannot_delete_other_couples_file(session, local_storage):
    _, _, couple = await seed_couple(session)

    with pytest.raises(AppError) as exc:
        await upload_service.delete_upload(couple, "couples/999/diaries/x.jpg")

    assert exc.value.code == 16004


async def test_diary_exposes_display_urls(session, local_storage):
    a, _, couple = await seed_couple(session)
    key = f"couples/{couple.id}/diaries/photo.jpg"

    diary = await diary_service.create(
        session, couple, a, DiaryCreate(content="有图", images=[key])
    )
    out = diary_service.to_out(diary)

    assert out.images == [key]
    assert out.image_urls == [f"/uploads/{key}"]
