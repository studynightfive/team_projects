"""文档批量处理与回收站状态机测试。"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.documents.models import Document, DocumentStatus, TaskStatus
from app.documents.schemas import DocumentIdBatchRequest
from app.documents.service import DocumentService


def _document() -> Document:
    return Document(
        id="document-1",
        knowledge_base_id="kb-1",
        title="医疗信息化方案",
        original_filename="医疗信息化方案.md",
        stored_filename="医疗信息化方案.md",
        folder_path="",
        extension=".md",
        mime_type="text/markdown",
        size_bytes=1024,
        content_hash="0" * 64,
        version=1,
        status=DocumentStatus.READY.value,
        ocr_enabled=False,
        language="chi_sim+eng",
        chunk_strategy="recursive",
        chunk_size=800,
        chunk_overlap=120,
        is_active_index=True,
        created_by="user-1",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def test_batch_request_removes_duplicate_document_ids() -> None:
    request = DocumentIdBatchRequest(
        document_ids=["document-1", "document-1", "document-2"]
    )

    assert request.document_ids == ["document-1", "document-2"]


@pytest.mark.asyncio
async def test_batch_delete_moves_document_to_recycle_bin(monkeypatch) -> None:
    document = _document()
    session = SimpleNamespace(
        get=AsyncMock(return_value=document),
        commit=AsyncMock(),
    )
    service = object.__new__(DocumentService)
    service.session = session
    service.settings = SimpleNamespace(document_recycle_days=30)
    service._cancel_open_tasks = AsyncMock()
    service._deactivate_index = AsyncMock()

    monkeypatch.setattr(
        "app.documents.service.require_any_permission",
        lambda *_args: None,
    )
    monkeypatch.setattr(
        "app.documents.service.user_can_access_kb",
        AsyncMock(return_value=True),
    )
    unpublish = AsyncMock()
    monkeypatch.setattr(
        "app.documents.service.unpublish_document_from_retrieval",
        unpublish,
    )

    result = await service.batch_delete(
        SimpleNamespace(id="user-1"),
        DocumentIdBatchRequest(document_ids=[document.id]),
    )

    assert result.deleted_count == 1
    assert document.status == DocumentStatus.CANCELLED.value
    assert document.deleted_at is not None
    assert document.purge_after is not None
    assert (document.purge_after - document.deleted_at).days == 30
    service._cancel_open_tasks.assert_awaited_once_with(document.id)
    service._deactivate_index.assert_awaited_once_with(document.id)
    unpublish.assert_awaited_once_with(session, document.id)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_reprocess_task_uses_real_document_task_progress() -> None:
    document = _document()
    session = SimpleNamespace(
        add=MagicMock(),
        flush=AsyncMock(),
    )
    service = object.__new__(DocumentService)
    service.session = session
    service._latest_task = AsyncMock(return_value=None)

    task = await service._create_reprocess_task(document, None)

    assert task.document_id == document.id
    assert task.status == TaskStatus.QUEUED.value
    assert task.progress == 0
    assert document.status == DocumentStatus.UPLOADED.value
    assert document.is_active_index is False
    session.add.assert_called_once_with(task)
    session.flush.assert_awaited_once()
