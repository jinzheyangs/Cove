from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DiaryCreate(BaseModel):
    mode: Literal["shared", "personal"] = "personal"
    title: str | None = Field(default=None, max_length=200)
    content: str = Field(min_length=1, max_length=20000)
    mood_tags: list[str] = Field(default_factory=list, max_length=10)
    location: str | None = Field(default=None, max_length=200)
    images: list[str] = Field(default_factory=list, max_length=20)
    # 「各自视角」：同一件事的两个人传同一个 event_id
    event_id: str | None = Field(default=None, max_length=36)


class DiaryUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    content: str | None = Field(default=None, min_length=1, max_length=20000)
    mood_tags: list[str] | None = Field(default=None, max_length=10)
    location: str | None = Field(default=None, max_length=200)
    images: list[str] | None = Field(default=None, max_length=20)


class DiaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: str | None
    mode: str
    title: str | None
    content: str
    mood_tags: list[str]
    location: str | None
    images: list[str]
    author_id: int
    created_at: datetime
    updated_at: datetime
