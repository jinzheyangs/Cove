"""用户模块的请求 / 响应结构。

这些模型同时承担接口校验和 OpenAPI 文档生成。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RegisterRequest(BaseModel):
    """注册请求。

    手机号只做格式校验，不做真实性验证（没有接短信），
    因此它实际上只是一个用户名。
    """

    phone: str = Field(pattern=r"^1[3-9]\d{9}$", description="中国大陆手机号")  #手机号
    password: str = Field(min_length=6, max_length=64)   #密码
    nickname: str = Field(min_length=1, max_length=50)   #昵称


class LoginRequest(BaseModel):
    """登录请求。不做格式校验，避免给撞库者额外信息。"""

    phone: str  #手机号
    password: str   #密码


class UserOut(BaseModel):
    """对外暴露的用户信息。

    刻意不包含 password_hash、deleted_at 等内部字段。
    from_attributes=True 让它可以由 ORM 对象直接转换。

    avatar 是存储 key，avatar_url 是当前可访问地址。
    编辑资料时回传 avatar，展示时用 avatar_url。
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: str
    nickname: str
    avatar: str | None = None   #存储oss对象
    avatar_url: str | None = None
    created_at: datetime    #创建时间


class ProfileUpdate(BaseModel):
    """更新个人资料。只传要改的字段。"""

    nickname: str | None = Field(default=None, min_length=1, max_length=50)
    # 头像的 object key，由 /uploads/avatar 返回
    avatar: str | None = Field(default=None, max_length=255)


class ChangePasswordRequest(BaseModel):
    """修改密码。新密码长度和注册保持一致。"""

    old_password: str = Field(min_length=1, max_length=64)
    new_password: str = Field(min_length=6, max_length=64)


class TokenOut(BaseModel):
    """登录 / 注册 / 刷新成功后的返回。

    - access_token：放在 Authorization: Bearer 里
    - refresh_token：只在这里返回原文，客户端需要安全保存
    - expires_in：access token 剩余秒数，前端据此决定何时刷新
    """

    access_token: str   #JWT 短时效令牌。前端请求头带上
    refresh_token: str  #随机字符串，存数据库，可以吊销。只有登录 / 刷新接口才返回一次原始值。
    token_type: str = "bearer"  #固定常量，告诉前端 Authorization 头的类型。
    # access_token 还有多少秒过期。前端拿到后自己计时，快过期时调用刷新接口。
    expires_in: int
    user: UserOut   #嵌套用户信息模型。


class RefreshRequest(BaseModel):
    """刷新或登出时提交 refresh token。"""

    refresh_token: str = Field(min_length=10, max_length=200)
