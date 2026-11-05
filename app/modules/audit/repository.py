"""数据访问层：审计日志。

约定：不 commit，由调用方的业务事务一起提交。
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog


async def create(session: AsyncSession, **values: object) -> AuditLog:
    """插入一条审计记录并 flush。

    调用方随后 commit；如果业务回滚，这条记录也会消失。
    """
    log = AuditLog(**values)
    session.add(log)
    await session.flush()
    return log


async def list_by_user(
    session: AsyncSession, user_id: int, limit: int, offset: int
) -> list[AuditLog]:
    """按用户查审计记录，时间倒序。

    只返回该用户自己发起的操作，不暴露对方的。
    """
    stmt = (
        select(AuditLog)
        .where(AuditLog.user_id == user_id)
        .order_by(AuditLog.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(await session.scalars(stmt))
