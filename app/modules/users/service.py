"""业务层：用户注册、认证与令牌生命周期。"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError
from app.core.ratelimit import get_limiter
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.users import repository as repo
from app.modules.users.models import User


async def register(session: AsyncSession, phone: str, password: str, nickname: str) -> User:
    if await repo.exists_phone(session, phone):
        raise AppError("该手机号已注册", code=1001, status_code=409)

    user = await repo.create(
        session,
        phone=phone,
        password_hash=hash_password(password),
        nickname=nickname,
    )
    try:
        await session.commit()
    except IntegrityError as exc:
        # 并发注册同一手机号时，唯一索引兜底
        await session.rollback()
        raise AppError("该手机号已注册", code=1001, status_code=409) from exc

    await session.refresh(user)
    return user


async def authenticate(session: AsyncSession, phone: str, password: str) -> User:
    limiter = get_limiter()
    fail_key = f"login_fail:{phone}"

    if await limiter.count(fail_key) >= settings.LOGIN_MAX_ATTEMPTS:
        raise AppError("尝试次数过多，请稍后再试", code=1003, status_code=429)

    user = await repo.get_by_phone(session, phone)
    if user is None or not verify_password(password, user.password_hash):
        await limiter.hit(fail_key, settings.LOGIN_MAX_ATTEMPTS, settings.LOGIN_LOCK_SECONDS)
        raise AppError("手机号或密码错误", code=1002, status_code=401)

    await limiter.reset(fail_key)
    return user


def _hash_refresh(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _refresh_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(days=settings.JWT_REFRESH_EXPIRE_DAYS)


async def issue_tokens(session: AsyncSession, user: User) -> tuple[str, str]:
    """签发 access token + refresh token。refresh 只返回原文一次，库里存哈希。"""
    raw = secrets.token_urlsafe(32)
    await repo.create_refresh_token(
        session,
        user_id=user.id,
        token_hash=_hash_refresh(raw),
        expires_at=_refresh_expiry(),
    )
    await session.commit()
    return create_access_token(user.id), raw


async def refresh_tokens(
    session: AsyncSession, raw_refresh: str
) -> tuple[str, str, User]:
    """刷新并轮换：旧 refresh 立即作废。"""
    token = await repo.get_refresh_by_hash(session, _hash_refresh(raw_refresh))
    now = datetime.now(UTC)
    if token is None or token.revoked_at is not None or token.expires_at <= now:
        raise AppError("登录已失效，请重新登录", code=1005, status_code=401)

    user = await repo.get_by_id(session, token.user_id)
    if user is None or user.deleted_at is not None:
        raise AppError("账号不存在", code=1006, status_code=401)

    await repo.revoke_refresh_token(session, token, now)
    new_raw = secrets.token_urlsafe(32)
    await repo.create_refresh_token(
        session,
        user_id=user.id,
        token_hash=_hash_refresh(new_raw),
        expires_at=_refresh_expiry(),
    )
    await session.commit()
    return create_access_token(user.id), new_raw, user


async def logout(session: AsyncSession, raw_refresh: str) -> None:
    token = await repo.get_refresh_by_hash(session, _hash_refresh(raw_refresh))
    if token is not None and token.revoked_at is None:
        await repo.revoke_refresh_token(session, token, datetime.now(UTC))
    await session.commit()


async def logout_all(session: AsyncSession, user: User) -> int:
    count = await repo.revoke_all_refresh_tokens(session, user.id, datetime.now(UTC))
    await session.commit()
    return count
