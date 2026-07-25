"""文档名称冲突预检与自动标识测试。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.common.exceptions import AppException
from app.documents.models import DuplicatePolicy
from app.documents.schemas import UploadOptions
from app.documents.service import DocumentService


class _ScalarResult:
    def __init__(self, values):
        self.values = values

    def scalars(self):
        return self.values


@pytest.mark.asyncio
async def test_name_conflict_preflight_reports_existing_and_batch_duplicates() -> None:
    existing = SimpleNamespace(
        id="document-1",
        title="医疗接口规范",
    )
    session = SimpleNamespace(execute=AsyncMock(return_value=_ScalarResult([existing])))
    service = object.__new__(DocumentService)
    service.session = session
    service._require_upload_access = AsyncMock()

    result = await service.check_name_conflicts(
        SimpleNamespace(id="user-1"),
        "kb-1",
        ["医疗接口规范.pdf", "新建方案.docx", "新建方案.pdf"],
    )

    assert [item.conflict_type for item in result.conflicts] == [
        "existing",
        "batch",
    ]
    assert result.conflicts[0].existing_document_id == existing.id
    assert result.conflicts[1].document_name == "新建方案"


@pytest.mark.asyncio
async def test_rename_policy_uses_next_available_readable_suffix() -> None:
    service = object.__new__(DocumentService)
    service._find_by_name = AsyncMock(side_effect=[SimpleNamespace(id="document-2"), None])

    title, filename = await service._next_available_name(
        "kb-1",
        "医疗接口规范.pdf",
    )

    assert title == "医疗接口规范 (3)"
    assert filename == "医疗接口规范 (3).pdf"


@pytest.mark.asyncio
async def test_batch_duplicate_is_not_treated_as_replaceable_existing_document() -> None:
    existing = SimpleNamespace(id="document-1", title="医疗接口规范")
    session = SimpleNamespace(execute=AsyncMock(return_value=_ScalarResult([existing])))
    service = object.__new__(DocumentService)
    service.session = session
    service._require_upload_access = AsyncMock()

    result = await service.check_name_conflicts(
        SimpleNamespace(id="user-1"),
        "kb-1",
        ["医疗接口规范.pdf", "医疗接口规范.docx"],
    )

    assert [item.conflict_type for item in result.conflicts] == [
        "existing",
        "batch",
    ]


@pytest.mark.asyncio
async def test_replace_policy_rejects_duplicate_names_inside_one_batch() -> None:
    service = object.__new__(DocumentService)
    service.settings = SimpleNamespace(max_upload_files=20)
    service._require_upload_access = AsyncMock()

    with pytest.raises(AppException, match="同一批文件包含同名文档"):
        await service.upload(
            SimpleNamespace(id="user-1"),
            "kb-1",
            [("医疗接口规范.pdf", b"pdf"), ("医疗接口规范.docx", b"docx")],
            UploadOptions(duplicate_policy=DuplicatePolicy.REPLACE),
        )
