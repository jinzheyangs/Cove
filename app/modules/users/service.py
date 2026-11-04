from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import hash_password, verify_password
from app.modules.users.models import User


async def register(session: AsyncSession, phone: str, password: str, nickname: str) -> User:
    existing = await session.scalar(select(User.id).where(User.phone == phone))
    if existing is not None:
        raise AppError("该手机号已注册", code=1001, status_code=409)

    user = User(phone=phone, password_hash=hash_password(password), nickname=nickname)
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        # 并发注册同一手机号时，唯一索引兜底
        await session.rollback()
        raise AppError("该手机号已注册", code=1001, status_code=409) from exc

    await session.refresh(user)
    return user


async def authenticate(session: AsyncSession, phone: str, password: str) -> User:
    user = await session.scalar(select(User).where(User.phone == phone))
    if user is None or not verify_password(password, user.password_hash):
        raise AppError("手机号或密码错误", code=1002, status_code=401)
    return user
