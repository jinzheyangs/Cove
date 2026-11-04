from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Envelope(BaseModel, Generic[T]):  # noqa: UP046 - Pydantic 泛型模型暂用旧写法
    """统一响应结构：{code, message, data}。"""

    code: int = 0
    message: str = "success"
    data: T | None = None
