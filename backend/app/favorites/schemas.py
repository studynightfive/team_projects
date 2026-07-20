"""Favorite API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

FavoriteType = Literal["answer", "document", "space", "query"]


class FavoriteCreate(BaseModel):
    type: FavoriteType
    title: str = Field(min_length=1, max_length=300)
    summary: str = Field(default="", max_length=4000)
    tags: list[str] = Field(default_factory=list)
    note: str = Field(default="", max_length=1000)
    source_id: str | None = Field(default=None, max_length=128)
    source_payload: dict[str, object] = Field(default_factory=dict)


class FavoriteUpdate(BaseModel):
    note: str | None = Field(default=None, max_length=1000)
    tags: list[str] | None = None


class FavoriteResponse(BaseModel):
    id: str
    type: FavoriteType
    title: str
    summary: str
    tags: list[str]
    note: str
    source_id: str | None = None
    source_payload: dict[str, object] = Field(default_factory=dict)
    saved_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}
