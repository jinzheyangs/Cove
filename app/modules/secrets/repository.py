"""数据访问层：秘密相关的所有 SQL 都在这里。"""

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.secrets.models import Secret


async def create(
    session: AsyncSession,
    *,
    couple_id: int,
    author_id: int,
    content: str,
    level: str,
    cost_coins: int,
    is_burn_after_read: bool,
) -> Secret:
    secret = Secret(
        couple_id=couple_id,
        author_id=author_id,
        content=content,
        level=level,
        cost_coins=cost_coins,
        is_burn_after_read=is_burn_after_read,
    )
    session.add(secret)
    await session.flush()
    return secret


async def get_for_update(session: AsyncSession, secret_id: int) -> Secret | None:
    return await session.scalar(
        select(Secret).where(Secret.id == secret_id).with_for_update()
    )


async def list_by_author(
    session: AsyncSession, couple_id: int, author_id: int
) -> list[Secret]:
    stmt = (
        select(Secret)
        .where(Secret.couple_id == couple_id, Secret.author_id == author_id)
        .order_by(Secret.id.desc())
    )
    return list(await session.scalars(stmt))


async def list_available(
    session: AsyncSession, couple_id: int, partner_id: int
) -> list[Secret]:
    stmt = (
        select(Secret)
        .where(
            Secret.couple_id == couple_id,
            Secret.author_id == partner_id,
            Secret.status == "active",
        )
        .order_by(Secret.id.desc())
    )
    return list(await session.scalars(stmt))


async def destroy_one(session: AsyncSession, secret: Secret) -> None:
    secret.status = "destroyed"
    secret.content = ""
    await session.flush()


async def destroy_all_of_author(
    session: AsyncSession, couple_id: int, author_id: int
) -> int:
    result = await session.execute(
        update(Secret)
        .where(
            Secret.couple_id == couple_id,
            Secret.author_id == author_id,
            Secret.status != "destroyed",
        )
        .values(status="destroyed", content="")
    )
    return result.rowcount or 0


async def purge_burned_before(session: AsyncSession, cutoff: datetime) -> int:
    """把燃尽期已过的秘密内容清空。"""
    result = await session.execute(
        update(Secret)
        .where(
            Secret.status == "burned",
            Secret.content != "",
            Secret.viewed_at < cutoff,
        )
        .values(content="")
    )
    return result.rowcount or 0
