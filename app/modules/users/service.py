"""业务层：用户注册、认证与令牌生命周期。

事务边界都在这层：每个公开函数结束时要么 commit，要么 rollback。
"""

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
    """注册新用户。

    先查一次是为了给出友好错误；真正的并发兜底靠数据库唯一索引，
    两个请求同时通过检查时，后到的那个会触发 IntegrityError。
    """
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
    """校验手机号 + 密码。

    带登录失败锁定：
    - 每次失败给 Redis 计数 +1
    - 达到阈值后直接拒绝，不再校验密码（防止暴力尝试）
    - 登录成功清零

    Redis 不可用时限流器会 fail open，此时退化为“不限次数”。
    """
    limiter = get_limiter()
    fail_key = f"login_fail:{phone}"

    if await limiter.count(fail_key) >= settings.LOGIN_MAX_ATTEMPTS:
        raise AppError("尝试次数过多，请稍后再试", code=1003, status_code=429)

    user = await repo.get_by_phone(session, phone)
    # 用户不存在和密码错误返回同一个错误，避免暴露手机号是否已注册
    if user is None or not verify_password(password, user.password_hash):
        await limiter.hit(fail_key, settings.LOGIN_MAX_ATTEMPTS, settings.LOGIN_LOCK_SECONDS)
        raise AppError("手机号或密码错误", code=1002, status_code=401)

    await limiter.reset(fail_key)
    return user


def _hash_refresh(raw: str) -> str:
    """刷新令牌入库前先哈希。

    用 sha256 而不是 argon2：refresh token 本身是 256 位随机串，
    不存在被字典攻击的风险，快速哈希足够。
    """
    return hashlib.sha256(raw.encode()).hexdigest()


def _refresh_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(days=settings.JWT_REFRESH_EXPIRE_DAYS)


async def issue_tokens(session: AsyncSession, user: User) -> tuple[str, str]:
    """签发一对新令牌。

    Returns:
        (access_token, refresh_token)。
        refresh_token 原文只在此刻返回一次，数据库里只有哈希。

    Side effect:
        会 commit，确保令牌落库后才返回给客户端。
    """
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
    """用 refresh token 换一对新令牌，并轮换旧令牌。

    安全设计：
    - 已吊销、已过期、不存在的 token 一律拒绝
    - 旧 token 立即吊销，即使本次响应在网络中丢失，旧 token 也不能再用
    - 账号已注销时拒绝刷新

    Returns:
        (新的 access_token, 新的 refresh_token, 用户)
    """
    token = await repo.get_refresh_by_hash(session, _hash_refresh(raw_refresh))
    now = datetime.now(UTC)
    if token is None or token.revoked_at is not None or token.expires_at <= now:
        raise AppError("登录已失效，请重新登录", code=1005, status_code=401)

    user = await repo.get_by_id(session, token.user_id)
    if user is None or user.deleted_at is not None:
        raise AppError("账号不存在", code=1006, status_code=401)

    # 先作废旧的，再发新的；两步在同一个事务里提交
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
    """吊销指定的 refresh token。

    找不到也静默成功：登出接口不应该告诉调用方“这个 token 存不存在”。
    """
    token = await repo.get_refresh_by_hash(session, _hash_refresh(raw_refresh))
    if token is not None and token.revoked_at is None:
        await repo.revoke_refresh_token(session, token, datetime.now(UTC))
    await session.commit()


async def logout_all(session: AsyncSession, user: User) -> int:
    """吊销该用户所有会话，返回被吊销的数量。

    用于“退出所有设备”或怀疑 token 泄露的场景。
    注意：access token 是无状态的，已签发的那些在过期前仍然有效
    （最长 JWT_ACCESS_EXPIRE_MINUTES 分钟）。
    """
    count = await repo.revoke_all_refresh_tokens(session, user.id, datetime.now(UTC))
    await session.commit()
    return count
