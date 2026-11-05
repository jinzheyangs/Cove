"""数据访问层：审计日志。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog


async def create(session: AsyncSession, **values: object) -> AuditLog:
    log = AuditLog(**values)
    session.add(log)
    await session.flush()
    return log


async def list_by_user(
    session: AsyncSession, user_id: int, limit: int, offset: int
) -> list[AuditLog]:
    stmt = (
        select(AuditLog)
        .where(AuditLog.user_id == user_id)
        .order_by(AuditLog.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(await session.scalars(stmt))
