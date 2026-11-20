"""数据访问层：秘密相关的所有 SQL 都在这里。

约定：不 commit，事务由 service 控制。
"""

from sqlalchemy import select
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
) -> Secret:
    """插入秘密。content 会由 EncryptedText 自动加密。"""
    secret = Secret(
        couple_id=couple_id,
        author_id=author_id,
        content=content,
        level=level,
        cost_coins=cost_coins,
    )
    session.add(secret)
    await session.flush()
    return secret


async def get_for_update(session: AsyncSession, secret_id: int) -> Secret | None:
    """加行锁读取秘密。

    摘取时必须锁：防止同一个人并发点两次，导致重复扣币或重复燃尽。
    """
    return await session.scalar(
        select(Secret).where(Secret.id == secret_id).with_for_update()
    )


async def list_by_author(
    session: AsyncSession, couple_id: int, author_id: int
) -> list[Secret]:
    """我发布的全部秘密（含已被摘走、已销毁）。"""
    stmt = (
        select(Secret)
        .where(Secret.couple_id == couple_id, Secret.author_id == author_id)
        .order_by(Secret.id.desc())
    )
    return list(await session.scalars(stmt))


async def list_available(
    session: AsyncSession, couple_id: int, partner_id: int
) -> list[Secret]:
    """对方发布的、还能摘取的秘密。

    只查 active，所以摘走销毁的不会出现在列表里。
    """
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
    """销毁单条：状态置为 destroyed，内容直接清空。"""
    secret.status = "destroyed"
    secret.content = ""
    await session.flush()
