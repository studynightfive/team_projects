"""知识库 API schemas。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    department_id: str | None = None


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    status: str | None = Field(default=None, pattern="^(active|archived)$")
    department_id: str | None = None


class KnowledgeBaseSummary(BaseModel):
    id: str
    name: str
    description: str | None = None
    department_id: str
    department_name: str
    kind: str
    owner_user_id: str | None = None
    status: str
    document_count: int = 0
    ready_document_count: int = 0
    chunk_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
