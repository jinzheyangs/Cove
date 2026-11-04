import pytest

from app.core.errors import AppError
from app.modules.todos import service
from app.modules.todos.schemas import TodoCreate
from tests.helpers import seed_couple


async def test_complete_generates_memory_card(session):
    a, _, couple = await seed_couple(session)
    todo = await service.create(
        session,
        couple,
        a,
        TodoCreate(category="想去的地方", title="一起去看海"),
    )

    completed, card = await service.complete(session, couple, a, todo.id)

    assert completed.status == "completed"
    assert completed.completed_at is not None
    assert card.title == "一起去看海"


async def test_cannot_complete_twice(session):
    a, _, couple = await seed_couple(session)
    todo = await service.create(
        session, couple, a, TodoCreate(category="技能", title="一起学做饭")
    )
    await service.complete(session, couple, a, todo.id)

    with pytest.raises(AppError) as exc:
        await service.complete(session, couple, a, todo.id)

    assert exc.value.code == 9003


async def test_cannot_edit_partners_personal_todo(session):
    a, b, couple = await seed_couple(session)
    todo = await service.create(
        session,
        couple,
        a,
        TodoCreate(type="personal", category="习惯", title="戒掉熬夜"),
    )

    with pytest.raises(AppError) as exc:
        await service.complete(session, couple, b, todo.id)

    assert exc.value.code == 9002


async def test_shared_todo_editable_by_partner(session):
    a, b, couple = await seed_couple(session)
    todo = await service.create(
        session, couple, a, TodoCreate(type="shared", category="约定", title="每周一起散步")
    )

    completed, _ = await service.complete(session, couple, b, todo.id)
    assert completed.status == "completed"
