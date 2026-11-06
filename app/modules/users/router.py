"""用户与认证的 HTTP 接口。

router 只负责：收参数、调 service、包成统一响应。
业务规则和事务都在 service 里。
"""

from fastapi import APIRouter

from app.core.config import settings
from app.core.deps import CurrentUser, SessionDep
from app.core.schemas import Envelope
from app.modules.users import service
from app.modules.users.models import User
from app.modules.users.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    ProfileUpdate,
    RefreshRequest,
    RegisterRequest,
    TokenOut,
    UserOut,
)

# /auth 下是公开接口，/users 下需要登录
auth_router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])


def _token_response(access: str, refresh: str, user: User) -> TokenOut:
    """把 service 的返回值组装成统一响应。

    expires_in 用秒表示，前端可以直接拿来做刷新倒计时。
    """
    return TokenOut(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.JWT_ACCESS_EXPIRE_MINUTES * 60,
        user=service.to_out(user),
    )


@auth_router.post("/register", response_model=Envelope[TokenOut])
async def register(body: RegisterRequest, session: SessionDep) -> Envelope[TokenOut]:
    """注册并直接返回登录态，省掉客户端再登录一次。"""
    user = await service.register(session, body.phone, body.password, body.nickname)
    access, refresh = await service.issue_tokens(session, user)
    return Envelope(data=_token_response(access, refresh, user))


@auth_router.post("/login", response_model=Envelope[TokenOut])
async def login(body: LoginRequest, session: SessionDep) -> Envelope[TokenOut]:
    """手机号 + 密码登录。

    连续失败会被锁定，错误码 1003；密码错误是 1002。
    """
    user = await service.authenticate(session, body.phone, body.password)
    access, refresh = await service.issue_tokens(session, user)
    return Envelope(data=_token_response(access, refresh, user))


@auth_router.post("/refresh", response_model=Envelope[TokenOut])
async def refresh(body: RefreshRequest, session: SessionDep) -> Envelope[TokenOut]:
    """用 refresh token 换新的一对令牌。

    旧 refresh token 会立即失效，客户端必须保存返回的新值。
    """
    access, refresh_token, user = await service.refresh_tokens(
        session, body.refresh_token
    )
    return Envelope(data=_token_response(access, refresh_token, user))


@auth_router.post("/logout", response_model=Envelope[None])
async def logout(body: RefreshRequest, session: SessionDep) -> Envelope[None]:
    """登出当前设备：吊销传入的 refresh token。"""
    await service.logout(session, body.refresh_token)
    return Envelope()


@auth_router.post("/logout-all", response_model=Envelope[dict])
async def logout_all(user: CurrentUser, session: SessionDep) -> Envelope[dict]:
    """退出所有设备：吊销该用户全部 refresh token。

    返回被吊销的会话数量。
    """
    count = await service.logout_all(session, user)
    return Envelope(data={"revoked": count})


@auth_router.post("/change-password", response_model=Envelope[TokenOut])
async def change_password(
    body: ChangePasswordRequest, user: CurrentUser, session: SessionDep
) -> Envelope[TokenOut]:
    """修改密码。

    成功后吊销全部 refresh token（其他设备需重新登录），
    当前设备会拿到一对新令牌。
    """
    access, refresh = await service.change_password(
        session, user, body.old_password, body.new_password
    )
    return Envelope(data=_token_response(access, refresh, user))


@users_router.get("/me", response_model=Envelope[UserOut])
async def me(user: CurrentUser) -> Envelope[UserOut]:
    """获取当前登录用户。依赖已保证 user 存在。"""
    return Envelope(data=service.to_out(user))


@users_router.put("/me", response_model=Envelope[UserOut])
async def update_me(
    body: ProfileUpdate, user: CurrentUser, session: SessionDep
) -> Envelope[UserOut]:
    """更新昵称 / 头像。

    avatar 传的是 /uploads/avatar 返回的 key，不是完整 URL。
    """
    updated = await service.update_profile(session, user, body)
    return Envelope(data=service.to_out(updated))
