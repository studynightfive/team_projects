"""文档原文、OCR 摘要与分块分页的聚焦回归测试。"""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.auth.dependencies import get_current_user
from app.common.config import settings as app_settings
from app.common.models import Permission, Role, User
from app.documents.models import Document, DocumentStatus
from app.documents.router import get_service
from app.documents.schemas import ChunkItem, DocumentDetail, OcrSummary
from app.documents.service import DocumentService, _ocr_manifest
from app.documents.storage import DocumentStorage
from app.main import app
from app.parsers.base import ParsedBlock, ParsedDocument


def _user() -> User:
    permission = Permission(
        id=str(uuid.uuid4()),
        code="document.view",
        name="document.view",
        module="documents",
        action="view",
    )
    role = Role(
        id=str(uuid.uuid4()),
        name="viewer",
        status="active",
        permissions=[permission],
    )
    return User(
        id=str(uuid.uuid4()),
        username="document-viewer",
        display_name="文档查看者",
        password_hash="not-used",
        status="active",
        roles=[role],
    )


def _detail() -> DocumentDetail:
    return DocumentDetail(
        id="document-1",
        knowledge_base_id="kb-1",
        title="医疗信息化",
        original_filename="医疗信息化.txt",
        folder_path="",
        extension=".txt",
        mime_type="text/plain",
        size_bytes=12,
        content_hash="0" * 64,
        version=1,
        status=DocumentStatus.READY.value,
        chunk_strategy="recursive",
        chunk_size=800,
        chunk_overlap=120,
        language="chi_sim+eng",
        ocr_enabled=True,
        is_active_index=True,
        ocr=OcrSummary(
            status="not_required",
            language="chi_sim+eng",
            review_required=False,
            message="解析器已直接提取文本，无需执行 OCR。",
        ),
    )


def test_ocr_manifest_marks_low_confidence_for_review() -> None:
    document = Document(
        id="document-1",
        knowledge_base_id="kb-1",
        title="扫描件",
        original_filename="scan.png",
        stored_filename="scan.png",
        folder_path="",
        extension=".png",
        mime_type="image/png",
        size_bytes=1,
        content_hash="0" * 64,
        version=1,
        status=DocumentStatus.OCR.value,
        ocr_enabled=True,
        language="chi_sim+eng",
    )
    parsed = ParsedDocument(
        title="扫描件",
        blocks=[
            ParsedBlock(
                text="识别文本",
                confidence=0.52,
                metadata={"source": "ocr"},
            )
        ],
    )

    summary = _ocr_manifest(document, parsed)

    assert summary["status"] == "low_confidence"
    assert summary["average_confidence"] == 0.52
    assert summary["review_required"] is True


@pytest.mark.asyncio
async def test_original_endpoint_uses_private_inline_response(
    client,
    tmp_path: Path,
) -> None:
    original = tmp_path / "医疗信息化.txt"
    original.write_text("医疗信息化正文", encoding="utf-8")
    service = MagicMock(spec=DocumentService)
    service.get_original_path = AsyncMock(return_value=(original, _detail()))
    user = _user()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_service] = lambda: service
    try:
        response = await client.get("/api/v1/documents/document-1/original")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.text == "医疗信息化正文"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-disposition"].startswith("inline;")
    service.get_original_path.assert_awaited_once_with(user, "document-1")


@pytest.mark.asyncio
async def test_chunks_endpoint_returns_paginated_data(client) -> None:
    chunk = ChunkItem(
        id="chunk-1",
        chunk_no=1,
        heading="核心模块",
        page_no=2,
        content="HIS、EMR、LIS",
        char_start=0,
        char_end=12,
        token_estimate=6,
        index_generation=2,
        is_active=True,
        embedding_status="vector",
    )
    service = MagicMock(spec=DocumentService)
    service.get_chunks = AsyncMock(return_value=([chunk], 21))
    user = _user()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_service] = lambda: service
    try:
        response = await client.get(
            "/api/v1/documents/document-1/chunks",
            params={"page": 2, "page_size": 20},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["data"]["total"] == 21
    assert response.json()["data"]["items"][0]["embedding_status"] == "vector"
    service.get_chunks.assert_awaited_once_with(
        user,
        "document-1",
        page=2,
        page_size=20,
    )


def test_storage_resolves_original_inside_document_directory(tmp_path: Path) -> None:
    settings = app_settings.model_copy(update={"storage_root": str(tmp_path)})
    storage = DocumentStorage(settings)
    expected = storage.save_original("document-1", "../../report.pdf", b"pdf")

    resolved = storage.resolve_original("document-1", "../../report.pdf")

    assert resolved == expected.resolve()
    assert resolved.parent == storage.original_dir("document-1").resolve()
