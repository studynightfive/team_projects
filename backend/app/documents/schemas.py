"""Pydantic schemas for document APIs (employee 4)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.documents.models import DuplicatePolicy


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
    page_count: int | None = None
    error_code: int | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class DocumentDetail(DocumentSummary):
    language: str
    ocr_enabled: bool
    markdown_path: str | None = None
    manifest_path: str | None = None
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
    manifest: dict


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
    def from_orm_task(cls, task: object) -> TaskResponse:
        return cls(
            task_id=task.id,  # type: ignore[attr-defined]
            task_type=task.task_type,  # type: ignore[attr-defined]
            status=task.status,  # type: ignore[attr-defined]
            stage=task.stage,  # type: ignore[attr-defined]
            progress=task.progress,  # type: ignore[attr-defined]
            retry_count=task.retry_count,  # type: ignore[attr-defined]
            error_code=task.error_code,  # type: ignore[attr-defined]
            error_message=task.error_message,  # type: ignore[attr-defined]
            request_id=task.request_id,  # type: ignore[attr-defined]
            created_at=task.created_at,  # type: ignore[attr-defined]
            finished_at=task.finished_at,  # type: ignore[attr-defined]
        )


class ReprocessRequest(BaseModel):
    ocr_enabled: bool | None = None
    language: str | None = None
    from_stage: str | None = Field(
        default=None,
        description="Optional safe restart stage; default rebuilds derived data",
    )


class UploadOptions(BaseModel):
    folder_path: str = ""
    ocr_enabled: bool = True
    language: str = "chi_sim+eng"
    duplicate_policy: DuplicatePolicy = DuplicatePolicy.NEW_VERSION
