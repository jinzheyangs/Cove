from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RegisterRequest(BaseModel):
    phone: str = Field(pattern=r"^1[3-9]\d{9}$", description="中国大陆手机号")
    password: str = Field(min_length=6, max_length=64)
    nickname: str = Field(min_length=1, max_length=50)


class LoginRequest(BaseModel):
    phone: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: str
    nickname: str
    avatar: str | None = None
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=200)
