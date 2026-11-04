from datetime import datetime

from pydantic import BaseModel, Field


class InquiryCreate(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class InputCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class InquiryOut(BaseModel):
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
