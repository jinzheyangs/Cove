from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Envelope(BaseModel, Generic[T]):
    """统一响应结构：{code, message, data}。"""

    code: int = 0
    message: str = "success"
    data: T | None = None
