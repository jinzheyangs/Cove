"""上传接口。

目前只开放日记图片。头像上传以后可以复用同一个 storage 层。
"""

from typing import Annotated

from fastapi import APIRouter, File, UploadFile

from app.core.config import settings
from app.core.deps import CurrentUser
from app.core.schemas import Envelope
from app.modules.couples.deps import CurrentCouple
from app.modules.uploads import service
from app.modules.uploads.schemas import UploadOut

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/diary-image", response_model=Envelope[UploadOut])
async def upload_diary_image(
    couple: CurrentCouple,
    file: Annotated[UploadFile, File(description="JPEG / PNG / WebP，最大 10MB")],
) -> Envelope[UploadOut]:
    """上传一张日记图片。

    前端拿到返回的 `key` 后，把它放进日记的 `images` 数组；
    `url` 只用于预览，不要存进数据库。
    """
    # 多读 1 字节，用来判断是否超过上限，避免把超大文件整个读进内存
    data = await file.read(settings.UPLOAD_MAX_BYTES + 1)
    result = await service.upload_diary_image(couple, file.content_type, data)
    return Envelope(data=result)


@router.post("/avatar", response_model=Envelope[UploadOut])
async def upload_avatar(
    user: CurrentUser,
    couple: CurrentCouple,
    file: Annotated[UploadFile, File(description="JPEG / PNG / WebP，最大 10MB")],
) -> Envelope[UploadOut]:
    """上传头像。

    返回的 key 需要再调用 PUT /users/me 设置到 avatar 字段。
    """
    data = await file.read(settings.UPLOAD_MAX_BYTES + 1)
    result = await service.upload_avatar(
        couple, user.id, file.content_type, data
    )
    return Envelope(data=result)


@router.delete("/{key:path}", response_model=Envelope[None])
async def delete_upload(key: str, couple: CurrentCouple) -> Envelope[None]:
    """删除当前关系内的一张图片。key 必须属于当前 couple。"""
    await service.delete_upload(couple, key)
    return Envelope()
