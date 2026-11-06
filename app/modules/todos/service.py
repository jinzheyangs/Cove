"""业务层：共同清单与单人清单。

权限规则：
- shared：双方都能改、能完成
- personal：只有创建者能改
"""

from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
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
    """新建清单项。默认进共同清单。"""
    key = body.idempotency_key
    if key:
        existing = await repo.get_by_idempotency_key(session, couple.id, key)
        if existing is not None:
            return existing

    try:
        todo = await repo.create(
            session,
            couple_id=couple.id,
            creator_id=creator.id,
            type=body.type,
            category=body.category,
            title=body.title,
            description=body.description,
            idempotency_key=key,
        )
        await session.commit()  # 提交事务，数据真正永久写到数据库
    except IntegrityError:
        # 并发提交同一个 key：唯一索引兜底，返回先成功的那条
        await session.rollback()
        existing = await repo.get_by_idempotency_key(session, couple.id, key)
        if existing is not None:
            return existing
        raise

    # 从数据库重新查一遍，把最新数据覆盖到本地 ORM 对象上
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
    """列出清单。前端用 type 切换共同 / 单人。"""
    return await repo.list_items(
        session, couple.id, item_type=item_type, category=category, status=status
    )


async def _get_editable(
    session: AsyncSession, couple: Couple, user: User, todo_id: int
) -> TodoItem:
    """取出可编辑的清单项。

    两个校验：
    1. 属于当前关系（防越权）
    2. 单人清单只有创建者能改
    """
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
    """部分更新。

    exclude_unset 保证只改客户端传了的字段。
    如果直接把状态改成 completed，顺手补上完成时间。
    """
    todo = await _get_editable(session, couple, user, todo_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(todo, field, value)
    if body.status == "completed" and todo.completed_at is None:
        todo.completed_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(todo)
    return todo


async def complete(
    session: AsyncSession, couple: Couple, user: User, todo_id: int
) -> tuple[TodoItem, MemoryCard]:
    """完成清单项，并生成一张纪念卡片。

    重复完成会报错，避免同一件事生成多张卡片。
    卡片目前只是文案，前端可以渲染成图片同步到日记。
    """
    todo = await _get_editable(session, couple, user, todo_id)
    if todo.status == "completed":
        raise AppError("这件事已经完成过了", code=9003, status_code=409)

    todo.status = "completed"
    todo.completed_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(todo)

    card = MemoryCard(
        title=todo.title,
        completed_at=todo.completed_at,
        note="又一起完成了一件事",
    )
    return todo, card


async def delete(session: AsyncSession, couple: Couple, user: User, todo_id: int) -> None:
    """删除。权限和修改一致。"""
    todo = await _get_editable(session, couple, user, todo_id)
    await repo.delete(session, todo)
    await session.commit()
