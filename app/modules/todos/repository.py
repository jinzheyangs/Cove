"""数据访问层：清单相关的所有 SQL 都在这里。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.todos.models import TodoItem


async def create(session: AsyncSession, *, couple_id: int, creator_id: int, **values) -> TodoItem:
    todo = TodoItem(couple_id=couple_id, creator_id=creator_id, **values)
    session.add(todo)
    await session.flush()
    return todo


async def get(session: AsyncSession, todo_id: int) -> TodoItem | None:
    return await session.get(TodoItem, todo_id)


async def list_items(
    session: AsyncSession,
    couple_id: int,
    *,
    item_type: str | None = None,
    category: str | None = None,
    status: str | None = None,
) -> list[TodoItem]:
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
    await session.delete(todo)
    await session.flush()
