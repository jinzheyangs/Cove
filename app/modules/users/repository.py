"""数据访问层：用户相关的所有 SQL 都在这里。

约定：这里只做查询和写入，**不 commit**。
事务边界由 service 层决定，这样多个写操作可以放进同一个事务。
"""

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import RefreshToken, User


async def get_by_id(session: AsyncSession, user_id: int) -> User | None:
    """按主键取用户。走 identity map，同一会话内重复调用不会重复查库。"""
    return await session.get(User, user_id)


async def get_by_phone(session: AsyncSession, phone: str) -> User | None:
    """按手机号取用户。手机号有唯一索引，最多一条。"""
    return await session.scalar(select(User).where(User.phone == phone))


async def exists_phone(session: AsyncSession, phone: str) -> bool:
    """只查 id，避免把整行数据取回来。用于注册前的快速判重。"""
    found = await session.scalar(select(User.id).where(User.phone == phone))
    return found is not None


async def create(
    session: AsyncSession, *, phone: str, password_hash: str, nickname: str
) -> User:
    """插入用户并 flush。

    flush 而不是 commit：拿得到自增 id，但事务仍由 service 控制。
    """
    user = User(phone=phone, password_hash=password_hash, nickname=nickname)
    session.add(user)
    await session.flush()
    return user


async def create_refresh_token(
    session: AsyncSession, *, user_id: int, token_hash: str, expires_at: datetime
) -> RefreshToken:
    """写入一条刷新令牌记录（存的是哈希，不是原文）。"""
    token = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    session.add(token)
    await session.flush()
    return token


async def get_refresh_by_hash(
    session: AsyncSession, token_hash: str
) -> RefreshToken | None:
    """按哈希查令牌。唯一索引保证最多一条。"""
    return await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )


async def revoke_refresh_token(
    session: AsyncSession, token: RefreshToken, now: datetime
) -> None:
    """吊销单条令牌。只打时间戳，不删记录，便于审计。"""
    token.revoked_at = now
    await session.flush()


async def revoke_all_refresh_tokens(
    session: AsyncSession, user_id: int, now: datetime
) -> int:
    """吊销该用户所有未吊销的令牌，返回影响行数。

    用户改密码、怀疑账号被盗、或者主动「退出所有设备」时调用。
    """
    result = await session.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    return result.rowcount or 0
