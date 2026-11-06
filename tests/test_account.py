"""账号设置：资料编辑、头像上传、修改密码与会话吊销。"""

import pytest

from app.core.errors import AppError
from app.core.storage import LocalStorage
from app.modules.uploads import service as upload_service
from app.modules.users import service as user_service
from app.modules.users.schemas import ProfileUpdate
from tests.helpers import TEST_PASSWORD, seed_couple

# 最小 PNG 文件头，服务只校验魔数
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 32


@pytest.fixture
def local_storage(tmp_path, monkeypatch):
    from app.core import storage as storage_module

    store = LocalStorage(tmp_path, "/uploads")
    monkeypatch.setattr(storage_module, "_storage", store)
    return store


async def test_update_nickname(session):
    a, _, _ = await seed_couple(session)

    updated = await user_service.update_profile(
        session, a, ProfileUpdate(nickname="新名字")
    )

    assert updated.nickname == "新名字"


async def test_update_avatar_requires_own_prefix(session, local_storage):
    a, _, couple = await seed_couple(session)

    with pytest.raises(AppError) as exc:
        await user_service.update_profile(
            session,
            a,
            ProfileUpdate(avatar=f"couples/{couple.id}/avatars/999/x.jpg"),
        )

    assert exc.value.code == 1009


async def test_avatar_upload_and_url(session, local_storage):
    a, _, couple = await seed_couple(session)

    result = await upload_service.upload_avatar(
        couple, a.id, "image/png", PNG_BYTES
    )

    assert result.key.startswith(f"couples/{couple.id}/avatars/{a.id}/")
    assert (local_storage.root / result.key).exists()

    await user_service.update_profile(session, a, ProfileUpdate(avatar=result.key))
    out = user_service.to_out(a)
    assert out.avatar == result.key
    assert out.avatar_url == f"/uploads/{result.key}"


async def test_change_password_rejects_wrong_old(session):
    a, _, _ = await seed_couple(session)

    with pytest.raises(AppError) as exc:
        await user_service.change_password(session, a, "wrong-pass", "newpass99")

    assert exc.value.code == 1007


async def test_change_password_rotates_sessions(session):
    a, _, _ = await seed_couple(session)
    _, old_refresh = await user_service.issue_tokens(session, a)

    await user_service.change_password(session, a, TEST_PASSWORD, "newpass99")

    # 旧密码失效，新密码可用
    with pytest.raises(AppError) as exc:
        await user_service.authenticate(session, a.phone, TEST_PASSWORD)
    assert exc.value.code == 1002
    assert (await user_service.authenticate(session, a.phone, "newpass99")).id == a.id

    # 旧 refresh token 被吊销
    with pytest.raises(AppError) as exc:
        await user_service.refresh_tokens(session, old_refresh)
    assert exc.value.code == 1005
