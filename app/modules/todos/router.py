from typing import Annotated

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, SessionDep
from app.core.schemas import Envelope
from app.modules.couples.deps import CurrentCouple
from app.modules.todos import service
from app.modules.todos.schemas import (
    TodoCompleteOut,
    TodoCreate,
    TodoOut,
    TodoUpdate,
)

router = APIRouter(prefix="/todos", tags=["todos"])


@router.post("", response_model=Envelope[TodoOut])
async def create(
    body: TodoCreate, user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[TodoOut]:
    todo = await service.create(session, couple, user, body)
    return Envelope(data=TodoOut.model_validate(todo))


@router.get("", response_model=Envelope[list[TodoOut]])
async def list_items(
    couple: CurrentCouple,
    session: SessionDep,
    type: Annotated[str | None, Query(pattern="^(shared|personal)$")] = None,
    category: str | None = None,
    status: Annotated[str | None, Query(pattern="^(pending|completed|cancelled)$")] = None,
) -> Envelope[list[TodoOut]]:
    items = await service.list_items(
        session, couple, item_type=type, category=category, status=status
    )
    return Envelope(data=[TodoOut.model_validate(i) for i in items])


@router.put("/{todo_id}", response_model=Envelope[TodoOut])
async def update(
    todo_id: int,
    body: TodoUpdate,
    user: CurrentUser,
    couple: CurrentCouple,
    session: SessionDep,
) -> Envelope[TodoOut]:
    todo = await service.update(session, couple, user, todo_id, body)
    return Envelope(data=TodoOut.model_validate(todo))


@router.post("/{todo_id}/complete", response_model=Envelope[TodoCompleteOut])
async def complete(
    todo_id: int, user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[TodoCompleteOut]:
    todo, card = await service.complete(session, couple, user, todo_id)
    return Envelope(data=TodoCompleteOut(todo=TodoOut.model_validate(todo), card=card))


@router.delete("/{todo_id}", response_model=Envelope[None])
async def delete(
    todo_id: int, user: CurrentUser, couple: CurrentCouple, session: SessionDep
) -> Envelope[None]:
    await service.delete(session, couple, user, todo_id)
    return Envelope()
