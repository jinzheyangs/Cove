"""数据访问层：清单相关的所有 SQL 都在这里。

约定：不 commit，事务由 service 控制。
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.todos.models import TodoItem


async def create(session: AsyncSession, *, couple_id: int, creator_id: int, **values) -> TodoItem:
    """插入清单项。"""
    todo = TodoItem(couple_id=couple_id, creator_id=creator_id, **values)
    session.add(todo)
    await session.flush()
    return todo


async def get_by_idempotency_key(
    session: AsyncSession, couple_id: int, key: str
) -> TodoItem | None:
    """按幂等键查已创建的清单项。"""
    return await session.scalar(
        select(TodoItem).where(
            TodoItem.couple_id == couple_id,
            TodoItem.idempotency_key == key,
        )
    )


async def get(session: AsyncSession, todo_id: int) -> TodoItem | None:
    """按主键读取。越权判断在 service 层。"""
    return await session.get(TodoItem, todo_id)


async def list_items(
    session: AsyncSession,
    couple_id: int,
    *,
    item_type: str | None = None,
    category: str | None = None,
    status: str | None = None,
) -> list[TodoItem]:
    """按关系查询，可选按类型、分类、状态过滤。

    排序是 status 字典序 + id 倒序。
    字典序为 cancelled < completed < pending，所以 pending 会排在最后。
    前端如果需要“未完成在前”，在客户端自行排序即可。
    """
    stmt = select(TodoItem).where(TodoItem.couple_id == couple_id)
    if item_type:
        stmt = stmt.where(TodoItem.type == item_type)
    if category:
        stmt = stmt.where(TodoItem.category == category)
    if status:
        stmt = stmt.where(TodoItem.status == status)
    stmt = stmt.order_by(TodoItem.status, TodoItem.id.desc())
    return list(await session.scalars(stmt))


async def delete(session: AsyncSession, todo: TodoItem) -> None:
    """物理删除。"""
    await session.delete(todo)
    await session.flush()
