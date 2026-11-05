"""隐私操作的请求结构。"""

from pydantic import BaseModel


class DeleteAccountRequest(BaseModel):
    """注销账号。

    必须重新输入密码：注销不可撤销，避免 token 被盗后被恶意注销。
    """

    password: str
