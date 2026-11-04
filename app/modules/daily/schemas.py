from datetime import date

from pydantic import BaseModel, Field


class DailyOut(BaseModel):
    day: date
    question: str
    my_answer: str | None
    # 自己回答之后才看得到对方的，避免互相影响
    partner_answer: str | None


class AnswerCreate(BaseModel):
    answer: str = Field(min_length=1, max_length=2000)
