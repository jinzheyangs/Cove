"""每日一问的请求 / 响应结构。"""

from datetime import date

from pydantic import BaseModel, Field


class DailyOut(BaseModel):
    """今日问题与双方回答。

    partner_answer 只有在自己回答之后才返回：
    先看到对方答案会显著影响自己写什么。
    """

    day: date
    question: str
    my_answer: str | None
    # 自己回答之后才看得到对方的，避免互相影响
    partner_answer: str | None


class AnswerCreate(BaseModel):
    """提交或修改今天的回答。"""

    answer: str = Field(min_length=1, max_length=2000)
