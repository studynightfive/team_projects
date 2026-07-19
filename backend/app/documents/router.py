"""Document and task HTTP routes (employee 4)."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_any_permission, require_permission
from app.common.database import get_db
from app.common.exceptions import AppException
from app.common.models import User
from app.common.schemas import APIResponse, ErrorCode, PaginatedData
from app.documents.models import DuplicatePolicy
from app.documents.schemas import (
    ReprocessRequest,
    UploadOptions,
)
from app.documents.service import DocumentService

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["documents"])


def get_service(db: AsyncSession = Depends(get_db)) -> DocumentService:
    return DocumentService(db)


@router.get("/knowledge-bases/{kb_id}/documents")
async def list_documents(
    kb_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("document.view")),
    service: DocumentService = Depends(get_service),
):
    request_id = str(uuid.uuid4())
    items, total = await service.list_documents(user, kb_id, page=page, page_size=page_size)
    return APIResponse(
        data=PaginatedData(items=items, page=page, page_size=page_size, total=total),
        request_id=request_id,
    )


@router.get("/admin/documents")
async def list_admin_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    status: str | None = Query(None),
    _user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.document.view")),
    service: DocumentService = Depends(get_service),
):
    items, total = await service.list_admin_documents(
        page=page,
        page_size=page_size,
        search=search,
        status=status,
    )
    return APIResponse(
        data=PaginatedData(items=items, page=page, page_size=page_size, total=total),
        request_id=str(uuid.uuid4()),
    )


@router.get("/admin/tasks")
async def list_admin_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    status: str | None = Query(None),
    _user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.task.view")),
    service: DocumentService = Depends(get_service),
):
    items, total = await service.list_admin_tasks(
        page=page,
        page_size=page_size,
        search=search,
        status=status,
    )
    return APIResponse(
        data=PaginatedData(items=items, page=page, page_size=page_size, total=total),
        request_id=str(uuid.uuid4()),
    )


@router.post("/knowledge-bases/{kb_id}/documents")
async def upload_documents(
    kb_id: str,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_any_permission("admin.document.upload", "document.upload")),
    service: DocumentService = Depends(get_service),
    files: list[UploadFile] = File(...),
    folder_path: str = Form(""),
    ocr_enabled: bool = Form(True),
    language: str = Form("chi_sim+eng"),
    duplicate_policy: str = Form("new_version"),
):
    request_id = str(uuid.uuid4())
    try:
        policy = DuplicatePolicy(duplicate_policy)
    except ValueError as exc:
        raise AppException(
            code=ErrorCode.UPLOAD_INVALID,
            message="duplicate_policy 无效",
            status_code=400,
            request_id=request_id,
        ) from exc

    payloads: list[tuple[str, bytes]] = []
    for upload in files:
        data = await upload.read()
        payloads.append((upload.filename or "unnamed", data))

    result = await service.upload(
        user,
        kb_id,
        payloads,
        UploadOptions(
            folder_path=folder_path,
            ocr_enabled=ocr_enabled,
            language=language,
            duplicate_policy=policy,
        ),
    )
    return APIResponse(data=result, request_id=request_id)


@router.get("/documents/{document_id}")
async def get_document(
    document_id: str,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("document.view")),
    service: DocumentService = Depends(get_service),
):
    data = await service.get_document(user, document_id)
    return APIResponse(data=data, request_id=str(uuid.uuid4()))


@router.get("/documents/{document_id}/markdown")
async def get_markdown(
    document_id: str,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("document.view")),
    service: DocumentService = Depends(get_service),
):
    data = await service.get_markdown(user, document_id)
    return APIResponse(data=data, request_id=str(uuid.uuid4()))


@router.get("/documents/{document_id}/chunks")
async def get_chunks(
    document_id: str,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("document.view")),
    service: DocumentService = Depends(get_service),
):
    data = await service.get_chunks(user, document_id)
    return APIResponse(data=data, request_id=str(uuid.uuid4()))


@router.get("/documents/{document_id}/assets/{asset_id}")
async def get_asset(
    document_id: str,
    asset_id: str,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("document.view")),
    service: DocumentService = Depends(get_service),
):
    path = await service.get_asset_path(user, document_id, asset_id)
    return FileResponse(path)


@router.post("/documents/{document_id}/reprocess")
async def reprocess_document(
    document_id: str,
    body: ReprocessRequest | None = None,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.document.upload")),
    service: DocumentService = Depends(get_service),
):
    data = await service.reprocess(user, document_id, body)
    return APIResponse(data=data, request_id=data.request_id)


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.document.delete")),
    service: DocumentService = Depends(get_service),
):
    await service.delete_document(user, document_id)
    return APIResponse(data=None, request_id=str(uuid.uuid4()))


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.task.view")),
    service: DocumentService = Depends(get_service),
):
    data = await service.get_task(user, task_id)
    return APIResponse(data=data, request_id=data.request_id)
