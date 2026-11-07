"""数据访问层：纪念日。

约定：不 commit，事务由 service 控制。
"""

from datetime import date as date_type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.anniversaries.models import Anniversary


async def create(
    session: AsyncSession,
    *,
    couple_id: int,
    created_by: int,
    title: str,
    date: date_type,
    repeat_yearly: bool,
    idempotency_key: str | None,
) -> Anniversary:
    row = Anniversary(
        couple_id=couple_id,
        created_by=created_by,
        title=title,
        date=date,
        repeat_yearly=repeat_yearly,
        idempotency_key=idempotency_key,
    )
    session.add(row)
    await session.flush()
    return row


async def get(session: AsyncSession, anniversary_id: int) -> Anniversary | None:
    return await session.get(Anniversary, anniversary_id)


async def get_by_idempotency_key(
    session: AsyncSession, couple_id: int, key: str
) -> Anniversary | None:
    return await session.scalar(
        select(Anniversary).where(
            Anniversary.couple_id == couple_id,
            Anniversary.idempotency_key == key,
        )
    )


async def list_by_couple(
    session: AsyncSession, couple_id: int
) -> list[Anniversary]:
    return list(
        await session.scalars(
            select(Anniversary)
            .where(Anniversary.couple_id == couple_id)
            .order_by(Anniversary.date, Anniversary.id)
        )
    )


async def delete(session: AsyncSession, row: Anniversary) -> None:
    await session.delete(row)
