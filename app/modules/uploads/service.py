"""业务层：图片上传与删除。

安全校验：
- 只接受 JPEG / PNG / WebP
- 同时检查 Content-Type 和文件头，防止伪造类型
- 限制大小，避免内存被大文件打满
- key 统一带上 couple_id 前缀，删除时校验归属
"""

import asyncio
from uuid import uuid4

from app.core.config import settings
from app.core.errors import AppError
from app.core.storage import get_storage
from app.modules.couples.models import Couple
from app.modules.uploads.schemas import UploadOut

# 允许的类型 -> (扩展名, 文件头)
_ALLOWED: dict[str, tuple[str, bytes]] = {
    "image/jpeg": (".jpg", b"\xff\xd8\xff"),
    "image/png": (".png", b"\x89PNG\r\n\x1a\n"),
    "image/webp": (".webp", b"RIFF"),  # 还要额外检查第 8-12 字节是 WEBP
}


def _check_content(content_type: str, data: bytes) -> None:
    """校验类型、文件头和大小。"""
    if not data:
        raise AppError("文件为空", code=16003, status_code=400)

    if content_type not in _ALLOWED:
        raise AppError("只支持 JPEG / PNG / WebP 图片", code=16001, status_code=400)

    if len(data) > settings.UPLOAD_MAX_BYTES:
        raise AppError("图片太大了", code=16002, status_code=413)

    magic = _ALLOWED[content_type][1]
    if content_type == "image/webp":
        if not (data[:4] == b"RIFF" and data[8:12] == b"WEBP"):
            raise AppError("文件内容与类型不符", code=16001, status_code=400)
    elif not data.startswith(magic):
        raise AppError("文件内容与类型不符", code=16001, status_code=400)


def _key_for(
    couple_id: int,
    ext: str,
    *,
    purpose: str = "diaries",
    user_id: int | None = None,
) -> str:
    """生成对象 key。

    结构：couples/{couple_id}/{用途}/{用户?}/{随机}.{ext}
    带 couple 前缀有两个作用：
    - 删除时能校验归属
    - 以后按关系批量清理时好定位
    """
    if user_id is not None:
        return f"couples/{couple_id}/{purpose}/{user_id}/{uuid4().hex}{ext}"
    return f"couples/{couple_id}/{purpose}/{uuid4().hex}{ext}"


async def _upload(
    couple: Couple,
    content_type: str | None,
    data: bytes,
    *,
    purpose: str,
    user_id: int | None = None,
) -> UploadOut:
    """校验并保存图片，返回 key 和可访问 URL。"""
    normalized = (content_type or "").split(";")[0].strip().lower()
    _check_content(normalized, data)  # 校验类型、文件头和大小。

    ext = _ALLOWED[normalized][0]  # 得到类型
    key = _key_for(couple.id, ext, purpose=purpose, user_id=user_id)
    storage = get_storage()  # 返回 oss 实例

    # 本地写盘和 OSS 上传都是阻塞操作，放到线程池，避免卡住事件循环
    await asyncio.to_thread(storage.save, key, data, normalized)

    return UploadOut(
        key=key,
        url=storage.build_url(key),
        size=len(data),
        content_type=normalized,
    )


async def upload_diary_image(
    couple: Couple, content_type: str | None, data: bytes
) -> UploadOut:
    """上传一张日记图片。"""
    return await _upload(couple, content_type, data, purpose="diaries")


async def upload_avatar(
    couple: Couple, user_id: int, content_type: str | None, data: bytes
) -> UploadOut:
    """上传头像。

    key 里带 user_id，PUT /users/me 时会校验前缀，
    防止把别人的头像地址填到自己头上。
    """
    return await _upload(
        couple, content_type, data, purpose="avatars", user_id=user_id
    )


async def delete_upload(couple: Couple, key: str) -> None:
    """删除自己关系内的图片。

    key 必须以当前 couple 前缀开头，否则视为越权。
    """
    prefix = f"couples/{couple.id}/"
    if not key.startswith(prefix):
        raise AppError("无权删除这个文件", code=16004, status_code=403)

    await asyncio.to_thread(get_storage().delete, key)
