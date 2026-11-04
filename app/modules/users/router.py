from fastapi import APIRouter

from app.core.deps import CurrentUser, SessionDep
from app.core.schemas import Envelope
from app.core.security import create_access_token
from app.modules.users import service
from app.modules.users.schemas import LoginRequest, RegisterRequest, TokenOut, UserOut

auth_router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])


@auth_router.post("/register", response_model=Envelope[TokenOut])
async def register(body: RegisterRequest, session: SessionDep) -> Envelope[TokenOut]:
    user = await service.register(session, body.phone, body.password, body.nickname)
    token = create_access_token(user.id)
    return Envelope(data=TokenOut(access_token=token, user=UserOut.model_validate(user)))


@auth_router.post("/login", response_model=Envelope[TokenOut])
async def login(body: LoginRequest, session: SessionDep) -> Envelope[TokenOut]:
    user = await service.authenticate(session, body.phone, body.password)
    token = create_access_token(user.id)
    return Envelope(data=TokenOut(access_token=token, user=UserOut.model_validate(user)))


@users_router.get("/me", response_model=Envelope[UserOut])
async def me(user: CurrentUser) -> Envelope[UserOut]:
    return Envelope(data=UserOut.model_validate(user))
