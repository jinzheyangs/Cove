"""数据访问层：用户相关的所有 SQL 都在这里。"""

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import RefreshToken, User


async def get_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def get_by_phone(session: AsyncSession, phone: str) -> User | None:
    return await session.scalar(select(User).where(User.phone == phone))


async def exists_phone(session: AsyncSession, phone: str) -> bool:
    found = await session.scalar(select(User.id).where(User.phone == phone))
    return found is not None


async def create(
    session: AsyncSession, *, phone: str, password_hash: str, nickname: str
) -> User:
    user = User(phone=phone, password_hash=password_hash, nickname=nickname)
    session.add(user)
    await session.flush()
    return user


async def create_refresh_token(
    session: AsyncSession, *, user_id: int, token_hash: str, expires_at: datetime
) -> RefreshToken:
    token = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    session.add(token)
    await session.flush()
    return token


async def get_refresh_by_hash(
    session: AsyncSession, token_hash: str
) -> RefreshToken | None:
    return await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )


async def revoke_refresh_token(
    session: AsyncSession, token: RefreshToken, now: datetime
) -> None:
    token.revoked_at = now
    await session.flush()


async def revoke_all_refresh_tokens(
    session: AsyncSession, user_id: int, now: datetime
) -> int:
    result = await session.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    return result.rowcount or 0
