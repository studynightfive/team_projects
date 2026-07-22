"""部门 API 数据结构。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DepartmentBrief(BaseModel):
    id: str
    name: str


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    admin_user_id: str


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    admin_user_id: str | None = None


class DepartmentResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    admin_user_id: str | None = None
    admin_username: str | None = None
    admin_display_name: str | None = None
    user_count: int = 0
    knowledge_base_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DepartmentListResponse(BaseModel):
    items: list[DepartmentResponse]
    total: int
