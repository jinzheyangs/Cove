"""业务层：共同清单与单人清单。"""

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.couples.models import Couple
from app.modules.todos import repository as repo
from app.modules.todos.models import TodoItem
from app.modules.todos.schemas import MemoryCard, TodoCreate, TodoUpdate
from app.modules.users.models import User


async def create(
    session: AsyncSession, couple: Couple, creator: User, body: TodoCreate
) -> TodoItem:
    todo = await repo.create(
        session,
        couple_id=couple.id,
        creator_id=creator.id,
        type=body.type,
        category=body.category,
        title=body.title,
        description=body.description,
    )
    await session.commit()
    await session.refresh(todo)
    return todo


async def list_items(
    session: AsyncSession,
    couple: Couple,
    *,
    item_type: str | None = None,
    category: str | None = None,
    status: str | None = None,
) -> list[TodoItem]:
    return await repo.list_items(
        session, couple.id, item_type=item_type, category=category, status=status
    )


async def _get_editable(
    session: AsyncSession, couple: Couple, user: User, todo_id: int
) -> TodoItem:
    todo = await repo.get(session, todo_id)
    if todo is None or todo.couple_id != couple.id:
        raise AppError("清单项不存在", code=9001, status_code=404)
    # 单人清单只有创建者能改；共同清单双方都能改
    if todo.type == "personal" and todo.creator_id != user.id:
        raise AppError("只能修改自己的清单", code=9002, status_code=403)
    return todo


async def update(
    session: AsyncSession, couple: Couple, user: User, todo_id: int, body: TodoUpdate
) -> TodoItem:
    todo = await _get_editable(session, couple, user, todo_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(todo, field, value)
    if body.status == "completed" and todo.completed_at is None:
        todo.completed_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(todo)
    return todo


async def complete(
    session: AsyncSession, couple: Couple, user: User, todo_id: int
) -> tuple[TodoItem, MemoryCard]:
    todo = await _get_editable(session, couple, user, todo_id)
    if todo.status == "completed":
        raise AppError("这件事已经完成过了", code=9003, status_code=409)

    todo.status = "completed"
    todo.completed_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(todo)

    card = MemoryCard(
        title=todo.title,
        completed_at=todo.completed_at,
        note="又一起完成了一件事",
    )
    return todo, card


async def delete(session: AsyncSession, couple: Couple, user: User, todo_id: int) -> None:
    todo = await _get_editable(session, couple, user, todo_id)
    await repo.delete(session, todo)
    await session.commit()
