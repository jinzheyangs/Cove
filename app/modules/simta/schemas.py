"""模拟TA 的请求 / 响应结构。"""

from typing import Literal

from pydantic import BaseModel, Field


class ConsentRequest(BaseModel):
    """开启或撤销数据授权。撤销立即生效。"""

    authorized: bool


class SettingsRequest(BaseModel):
    """切换忠实度。默认更贴近真实。"""

    fidelity: Literal["faithful", "idealized"] = "faithful"


class ChatRequest(BaseModel):
    """对分身说一句话。"""

    message: str = Field(min_length=1, max_length=2000)


class PersonaStateOut(BaseModel):
    """当前授权与偏好状态。

    同时返回「我授权了吗」和「对方授权了吗」，
    前端可以据此决定是否禁用聊天入口。
    """

    # 我是否允许对方用我的数据做模拟
    my_consent: bool
    # 对方是否允许我用 TA 的数据做模拟
    partner_consent: bool
    fidelity: str


class ChatResponse(BaseModel):
    """分身回复。

    disclaimer 必须和 reply 一起展示：
    不能让用户把模拟内容误当成真人的真实表达。
    """

    reply: str
    fidelity: str
    disclaimer: str
