"""模拟TA 的请求 / 响应结构。"""

from pydantic import BaseModel


class ConsentRequest(BaseModel):
    """开启或撤销数据授权。撤销立即生效。"""

    authorized: bool


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
