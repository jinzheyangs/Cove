from typing import Literal

from pydantic import BaseModel, Field


class ConsentRequest(BaseModel):
    authorized: bool


class SettingsRequest(BaseModel):
    fidelity: Literal["faithful", "idealized"] = "faithful"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class PersonaStateOut(BaseModel):
    # 我是否允许对方用我的数据做模拟
    my_consent: bool
    # 对方是否允许我用 TA 的数据做模拟
    partner_consent: bool
    fidelity: str


class ChatResponse(BaseModel):
    reply: str
    fidelity: str
    disclaimer: str
