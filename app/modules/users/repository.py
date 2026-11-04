"""数据访问层：用户相关的所有 SQL 都在这里。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User


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
