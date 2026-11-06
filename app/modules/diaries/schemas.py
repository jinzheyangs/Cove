"""日记模块的请求 / 响应结构。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DiaryCreate(BaseModel):
    """创建日记。

    event_id 由客户端生成（通常是 UUID）：
    两个人写同一件事时传同一个值，就能在查询时把两种视角聚到一起。
    """

    mode: Literal["shared", "personal"] = "personal"
    title: str | None = Field(default=None, max_length=200)
    content: str = Field(min_length=1, max_length=20000)
    mood_tags: list[str] = Field(default_factory=list, max_length=10)
    location: str | None = Field(default=None, max_length=200)
    images: list[str] = Field(default_factory=list, max_length=20)
    # 「各自视角」：同一件事的两个人传同一个 event_id
    event_id: str | None = Field(default=None, max_length=36)
    # 客户端生成的稳定值（如 UUID），重复提交只创建一条
    idempotency_key: str | None = Field(default=None, max_length=64)


class DiaryUpdate(BaseModel):
    """部分更新。

    所有字段都是可选的，service 用 exclude_unset 只改传了的字段，
    这样“只改标题”不会把正文清空。
    """

    title: str | None = Field(default=None, max_length=200)
    content: str | None = Field(default=None, min_length=1, max_length=20000)
    mood_tags: list[str] | None = Field(default=None, max_length=10)
    location: str | None = Field(default=None, max_length=200)
    images: list[str] | None = Field(default=None, max_length=20)


class DiaryOut(BaseModel):
    """日记详情。content 返回时已解密。

    图片相关有两个字段：
    - `images`：数据库里的 object key，编辑时应原样回传
    - `image_urls`：当前可访问的地址，只用于展示，不要入库
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: str | None
    mode: str
    title: str | None
    content: str
    mood_tags: list[str]
    location: str | None
    # 存储 key，编辑时回传
    images: list[str]
    # 展示 URL，由存储后端按需生成
    image_urls: list[str] = Field(default_factory=list)
    author_id: int
    created_at: datetime
    updated_at: datetime
