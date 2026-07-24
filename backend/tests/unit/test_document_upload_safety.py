"""文档上传事务、任务权限与公开契约的聚焦回归测试。"""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.common.config import settings as app_settings
from app.common.exceptions import AppException, ForbiddenException
from app.common.models import Permission, Role, User
from app.documents import service as document_service
from app.documents.models import (
    Document,
    DocumentStatus,
    DocumentTask,
    DuplicatePolicy,
    TaskStatus,
)
from app.documents.router import get_service
from app.documents.schemas import (
    DocumentDetail,
    ReprocessRequest,
    TaskResponse,
    UploadOptions,
)
from app.documents.service import DocumentService
from app.documents.storage import DocumentStorage, compute_sha256
from app.main import app


def _user(*permission_codes: str) -> User:
    permissions = [
        Permission(
            id=str(uuid.uuid4()),
            code=code,
            name=code,
            module="documents",
            action="test",
        )
        for code in permission_codes
    ]
    role = Role(
        id=str(uuid.uuid4()),
        name=f"role-{uuid.uuid4()}",
        status="active",
        permissions=permissions,
    )
    return User(
        id=str(uuid.uuid4()),
        username=f"user-{uuid.uuid4()}",
        display_name="测试用户",
        password_hash="not-used",
        status="active",
        roles=[role],
    )


def _session() -> MagicMock:
    session = MagicMock(spec=AsyncSession)
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


def _service(tmp_path: Path, session: MagicMock, *, max_upload_bytes: int) -> DocumentService:
    settings = app_settings.model_copy(
        update={
            "storage_root": str(tmp_path),
            "max_upload_bytes": max_upload_bytes,
            "worker_inline": False,
        }
    )
    storage = DocumentStorage(settings)
    return DocumentService(session, settings=settings, storage=storage)


@pytest.mark.asyncio
async def test_batch_failure_removes_files_created_by_earlier_items(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    service = _service(tmp_path, session, max_upload_bytes=4)
    monkeypatch.setattr(document_service, "user_can_access_kb", AsyncMock(return_value=True))
    monkeypatch.setattr(service, "_get_kb", AsyncMock())
    monkeypatch.setattr(service, "_find_by_hash", AsyncMock(return_value=None))
    monkeypatch.setattr(service, "_find_by_name", AsyncMock(return_value=None))

    with pytest.raises(AppException):
        await service.upload(
            _user("document.upload"),
            "kb-1",
            [("first.txt", b"one"), ("second.txt", b"12345")],
            UploadOptions(),
        )

    session.rollback.assert_awaited_once_with()
    session.commit.assert_not_awaited()
    assert list(service.storage.root.iterdir()) == []


@pytest.mark.asyncio
async def test_replace_failure_restores_original_and_derived_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    service = _service(tmp_path, session, max_upload_bytes=4)
    existing = Document(
        id="document-1",
        knowledge_base_id="kb-1",
        title="旧文档",
        original_filename="original.txt",
        stored_filename="original.txt",
        folder_path="old",
        extension=".txt",
        mime_type="text/plain",
        size_bytes=3,
        content_hash=compute_sha256(b"new"),
        version=1,
        status=DocumentStatus.READY.value,
        ocr_enabled=True,
        language="chi_sim+eng",
        is_active_index=True,
        created_by="user-1",
    )
    service.storage.save_original(existing.id, existing.stored_filename, b"old")
    service.storage.write_markdown_package(
        existing.id,
        "old markdown",
        {"version": 1},
        [("asset.txt", b"old asset")],
    )
    monkeypatch.setattr(document_service, "user_can_access_kb", AsyncMock(return_value=True))
    monkeypatch.setattr(service, "_get_kb", AsyncMock())
    monkeypatch.setattr(service, "_find_by_hash", AsyncMock(return_value=existing))
    monkeypatch.setattr(service, "_find_by_name", AsyncMock(return_value=existing))
    monkeypatch.setattr(service, "_deactivate_index", AsyncMock())

    with pytest.raises(AppException):
        await service.upload(
            _user("document.upload"),
            "kb-1",
            [("original.txt", b"new"), ("second.txt", b"12345")],
            UploadOptions(duplicate_policy=DuplicatePolicy.REPLACE),
        )

    original = service.storage.original_dir(existing.id) / "original.txt"
    assert original.read_bytes() == b"old"
    assert service.storage.read_markdown(existing.id) == "old markdown"
    assert service.storage.read_manifest(existing.id) == {"version": 1}
    assert (service.storage.assets_dir(existing.id) / "asset.txt").read_bytes() == b"old asset"
    backup_root = service.storage.root / ".upload-backups"
    assert not backup_root.exists() or list(backup_root.iterdir()) == []
    replacement_task = next(
        call.args[0]
        for call in session.add.call_args_list
        if isinstance(call.args[0], DocumentTask)
    )
    assert ":replace:" in replacement_task.idempotency_key
    assert len(replacement_task.idempotency_key) <= 128
    session.rollback.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_reprocess_idempotency_key_fits_database_column(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    service = _service(tmp_path, session, max_upload_bytes=4)
    document = Document(
        id=str(uuid.uuid4()),
        knowledge_base_id=str(uuid.uuid4()),
        title="待重处理文档",
        original_filename="document.txt",
        stored_filename="document.txt",
        folder_path="",
        extension=".txt",
        mime_type="text/plain",
        size_bytes=1,
        content_hash="0" * 64,
        version=1,
        status=DocumentStatus.FAILED.value,
        ocr_enabled=True,
        language="chi_sim+eng",
    )
    monkeypatch.setattr(service, "_latest_task", AsyncMock(return_value=None))

    task = await service._create_reprocess_task(document, None)

    assert ":retry:1:" in task.idempotency_key
    assert len(task.idempotency_key) <= 128


@pytest.mark.asyncio
async def test_upload_permission_can_query_own_kb_task(client) -> None:
    user = _user("document.upload")
    task = TaskResponse(
        task_id="task-1",
        task_type="document_convert",
        status=TaskStatus.QUEUED.value,
        stage=DocumentStatus.UPLOADED.value,
        progress=5,
        retry_count=0,
        request_id="request-1",
    )
    service = MagicMock(spec=DocumentService)
    service.get_task = AsyncMock(return_value=task)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_service] = lambda: service
    try:
        response = await client.get("/api/v1/tasks/task-1")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["data"]["task_id"] == "task-1"
    service.get_task.assert_awaited_once_with(user, "task-1")


@pytest.mark.asyncio
async def test_upload_permission_cannot_query_task_without_kb_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = DocumentTask(
        id="task-1",
        document_id="document-1",
        task_type="document_convert",
        status=TaskStatus.QUEUED.value,
        stage=DocumentStatus.UPLOADED.value,
        progress=5,
        retry_count=0,
        idempotency_key="task-1",
        request_id="request-1",
    )
    document = Document(
        id="document-1",
        knowledge_base_id="other-kb",
        title="文档",
        original_filename="document.txt",
        stored_filename="document.txt",
        folder_path="",
        extension=".txt",
        mime_type="text/plain",
        size_bytes=1,
        content_hash="0" * 64,
        version=1,
        status=DocumentStatus.UPLOADED.value,
        ocr_enabled=True,
        language="chi_sim+eng",
    )
    session = _session()
    session.get = AsyncMock(side_effect=[task, document])
    service = _service(tmp_path, session, max_upload_bytes=4)
    monkeypatch.setattr(document_service, "user_can_access_kb", AsyncMock(return_value=False))

    with pytest.raises(ForbiddenException):
        await service.get_task(_user("document.upload"), task.id)


def test_document_detail_does_not_expose_storage_paths() -> None:
    properties = DocumentDetail.model_json_schema()["properties"]
    assert "markdown_path" not in properties
    assert "manifest_path" not in properties


@pytest.mark.parametrize(
    ("schema", "payload"),
    [
        (UploadOptions, {"folder_path": "f" * 1001}),
        (UploadOptions, {"language": "l" * 65}),
        (ReprocessRequest, {"language": "l" * 65}),
        (ReprocessRequest, {"from_stage": "s" * 33}),
    ],
)
def test_document_option_fields_respect_database_lengths(
    schema: type[UploadOptions] | type[ReprocessRequest],
    payload: dict[str, str],
) -> None:
    with pytest.raises(ValidationError):
        schema.model_validate(payload)
