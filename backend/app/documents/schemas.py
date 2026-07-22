"""Pydantic schemas for document APIs (employee 4)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, JsonValue, model_validator

from app.documents.models import DocumentTask, DuplicatePolicy


class DocumentSummary(BaseModel):
    id: str
    knowledge_base_id: str
    title: str
    original_filename: str
    folder_path: str
    extension: str
    mime_type: str
    size_bytes: int
    content_hash: str
    version: int
    status: str
    parser_name: str | None = None
    chunk_strategy: str
    chunk_size: int
    chunk_overlap: int
    page_count: int | None = None
    error_code: int | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class DocumentDetail(DocumentSummary):
    language: str
    ocr_enabled: bool
    is_active_index: bool = False


class UploadResultItem(BaseModel):
    document: DocumentSummary
    task_id: str
    skipped: bool = False
    message: str | None = None


class UploadResponse(BaseModel):
    items: list[UploadResultItem]


class MarkdownContent(BaseModel):
    document_id: str
    content: str
    manifest: dict[str, JsonValue]


class ChunkItem(BaseModel):
    id: str
    chunk_no: int
    section_no: int | None = None
    heading: str | None = None
    page_no: int | None = None
    content: str
    char_start: int
    char_end: int
    is_active: bool

    model_config = {"from_attributes": True}


class TaskResponse(BaseModel):
    task_id: str
    task_type: str
    status: str
    stage: str
    progress: float
    retry_count: int
    error_code: int | None = None
    error_message: str | None = None
    request_id: str
    created_at: datetime | None = None
    finished_at: datetime | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_task(cls, task: DocumentTask) -> TaskResponse:
        return cls(
            task_id=task.id,
            task_type=task.task_type,
            status=task.status,
            stage=task.stage,
            progress=task.progress,
            retry_count=task.retry_count,
            error_code=task.error_code,
            error_message=task.error_message,
            request_id=task.request_id,
            created_at=task.created_at,
            finished_at=task.finished_at,
        )


class AdminDocumentItem(DocumentSummary):
    knowledge_base_name: str


class AdminTaskItem(TaskResponse):
    document_id: str
    document_title: str
    knowledge_base_id: str
    knowledge_base_name: str
    started_at: datetime | None = None


class ReprocessRequest(BaseModel):
    ocr_enabled: bool | None = None
    language: str | None = Field(default=None, min_length=1, max_length=64)
    chunk_strategy: Literal["fixed", "semantic", "recursive", "format"] | None = None
    chunk_size: int | None = Field(default=None, ge=100, le=4000)
    chunk_overlap: int | None = Field(default=None, ge=0, le=1000)
    from_stage: str | None = Field(
        default=None,
        max_length=32,
        description="Optional safe restart stage; default rebuilds derived data",
    )


class UploadOptions(BaseModel):
    folder_path: str = Field(default="", max_length=1000)
    ocr_enabled: bool = True
    language: str = Field(default="chi_sim+eng", min_length=1, max_length=64)
    duplicate_policy: DuplicatePolicy = DuplicatePolicy.NEW_VERSION
    chunk_strategy: Literal["fixed", "semantic", "recursive", "format"] = "recursive"
    chunk_size: int = Field(default=800, ge=100, le=4000)
    chunk_overlap: int = Field(default=120, ge=0, le=1000)

    @model_validator(mode="after")
    def validate_chunk_window(self) -> UploadOptions:
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap 必须小于 chunk_size")
        return self
