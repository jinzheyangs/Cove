"""通用响应结构。"""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Envelope(BaseModel, Generic[T]):  # noqa: UP046 - Pydantic 泛型模型暂用旧写法
    """统一响应外壳。

    用法：
        return Envelope(data=UserOut.model_validate(user))

    路由的 response_model 写成 `Envelope[UserOut]`，
    FastAPI 就能自动生成正确的 OpenAPI 文档。
    """

    code: int = 0
    message: str = "success"
    data: T | None = None
