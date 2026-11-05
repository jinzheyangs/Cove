from fastapi import APIRouter

from app.core.config import settings
from app.core.deps import CurrentUser, SessionDep
from app.core.schemas import Envelope
from app.modules.users import service
from app.modules.users.models import User
from app.modules.users.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenOut,
    UserOut,
)

auth_router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])


def _token_response(access: str, refresh: str, user: User) -> TokenOut:
    return TokenOut(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.JWT_ACCESS_EXPIRE_MINUTES * 60,
        user=UserOut.model_validate(user),
    )


@auth_router.post("/register", response_model=Envelope[TokenOut])
async def register(body: RegisterRequest, session: SessionDep) -> Envelope[TokenOut]:
    user = await service.register(session, body.phone, body.password, body.nickname)
    access, refresh = await service.issue_tokens(session, user)
    return Envelope(data=_token_response(access, refresh, user))


@auth_router.post("/login", response_model=Envelope[TokenOut])
async def login(body: LoginRequest, session: SessionDep) -> Envelope[TokenOut]:
    user = await service.authenticate(session, body.phone, body.password)
    access, refresh = await service.issue_tokens(session, user)
    return Envelope(data=_token_response(access, refresh, user))


@auth_router.post("/refresh", response_model=Envelope[TokenOut])
async def refresh(body: RefreshRequest, session: SessionDep) -> Envelope[TokenOut]:
    access, refresh_token, user = await service.refresh_tokens(
        session, body.refresh_token
    )
    return Envelope(data=_token_response(access, refresh_token, user))


@auth_router.post("/logout", response_model=Envelope[None])
async def logout(body: RefreshRequest, session: SessionDep) -> Envelope[None]:
    await service.logout(session, body.refresh_token)
    return Envelope()


@auth_router.post("/logout-all", response_model=Envelope[dict])
async def logout_all(user: CurrentUser, session: SessionDep) -> Envelope[dict]:
    count = await service.logout_all(session, user)
    return Envelope(data={"revoked": count})


@users_router.get("/me", response_model=Envelope[UserOut])
async def me(user: CurrentUser) -> Envelope[UserOut]:
    return Envelope(data=UserOut.model_validate(user))
