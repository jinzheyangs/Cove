"""业务层：写审计记录。

审计记录和业务操作在同一个事务里：
业务回滚时审计也不会留下脏数据，避免出现“记录了但没发生”。
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
    """写一条审计记录（不提交）。

    IP 和 request_id 从 structlog 上下文里取，
    这两个值由 RequestContextMiddleware 在每个请求开始时绑定。

    detail 只放元信息，例如 {"count": 3} 或 {"reason": "..."}，
    不要放秘密、日记、消息的正文。
    """
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
    """查看自己的敏感操作记录。"""
    return await repo.list_by_user(session, user_id, limit, offset)
