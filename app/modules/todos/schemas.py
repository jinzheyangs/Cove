from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TodoCreate(BaseModel):
    type: Literal["shared", "personal"] = "shared"
    category: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)


class TodoUpdate(BaseModel):
    category: str | None = Field(default=None, min_length=1, max_length=50)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    status: Literal["pending", "completed", "cancelled"] | None = None


class TodoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    category: str
    title: str
    description: str | None
    status: str
    creator_id: int
    completed_at: datetime | None
    created_at: datetime


class MemoryCard(BaseModel):
    title: str
    completed_at: datetime
    note: str


class TodoCompleteOut(BaseModel):
    todo: TodoOut
    card: MemoryCard
