"""知识库 API schemas。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    chunk_size: int = Field(default=800, ge=200, le=4000)
    chunk_overlap: int = Field(default=120, ge=0, le=1000)


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    status: str | None = Field(default=None, pattern="^(active|archived)$")
    chunk_size: int | None = Field(default=None, ge=200, le=4000)
    chunk_overlap: int | None = Field(default=None, ge=0, le=1000)


class KnowledgeBaseSummary(BaseModel):
    id: str
    name: str
    description: str | None = None
    status: str
    chunk_size: int
    chunk_overlap: int
    document_count: int = 0
    ready_document_count: int = 0
    chunk_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
