"""上传模块的响应结构。"""

from pydantic import BaseModel


class UploadOut(BaseModel):
    """上传成功后的结果。

    前端应该把 `key` 存进日记的 images 数组，
    展示时用 `url`；不要反过来把 url 存进数据库。
    """

    key: str
    url: str
    size: int
    content_type: str
