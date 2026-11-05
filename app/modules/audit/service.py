"""业务层：写审计记录。

审计记录和业务操作在同一个事务里，业务回滚时审计也不会留下脏数据。
"""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit import repository as repo
from app.modules.audit.models import AuditLog


async def record(
    session: AsyncSession,
    *,
    user_id: int,
    action: str,
    couple_id: int | None = None,
    target_type: str | None = None,
    target_id: int | None = None,
    detail: dict | None = None,
) -> AuditLog:
    ctx = structlog.contextvars.get_contextvars()
    return await repo.create(
        session,
        user_id=user_id,
        couple_id=couple_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
        ip=ctx.get("client_ip"),
        request_id=ctx.get("request_id"),
    )


async def list_mine(
    session: AsyncSession, user_id: int, limit: int, offset: int
) -> list[AuditLog]:
    return await repo.list_by_user(session, user_id, limit, offset)
