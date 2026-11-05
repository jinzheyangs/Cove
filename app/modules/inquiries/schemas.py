"""询问中心的请求 / 响应结构。"""

from datetime import datetime

from pydantic import BaseModel, Field


class InquiryCreate(BaseModel):
    """发起一个共同提问。"""

    question: str = Field(min_length=1, max_length=500)


class InputCreate(BaseModel):
    """提交想法或补充意见。"""

    content: str = Field(min_length=1, max_length=5000)


class InquiryOut(BaseModel):
    """询问详情。

    inputs 只在双方都提交后才返回内容：
    否则先写的人会影响后写的人，匿名就失去意义了。
    """

    id: int
    question: str
    status: str
    ai_response: str | None
    submitted_count: int
    my_input_submitted: bool
    # 双方都提交后才返回内容，避免先写的人被影响
    inputs: list[str]
    supplements: list[str]
    created_at: datetime
    closed_at: datetime | None
