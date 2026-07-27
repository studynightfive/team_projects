"""知识库归档状态的后端边界测试。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.common.exceptions import AppException
from app.common.schemas import ErrorCode
from app.documents.service import DocumentService
from app.knowledge import service as knowledge_service
from app.rag._shared.permissions import get_user_accessible_kb_ids


class _Rows:
    def fetchall(self) -> list[tuple[str]]:
        return [("kb-active",)]


class _DepartmentAdmin:
    def scalar_one_or_none(self) -> None:
        return None


class _KnowledgeRows:
    def scalars(self) -> list[object]:
        return []


@pytest.mark.asyncio
async def test_rag_accessible_scope_only_queries_active_knowledge_bases() -> None:
    db = SimpleNamespace(execute=AsyncMock(return_value=_Rows()))
    user = SimpleNamespace(id="user-1", department_id="department-1", roles=[])

    result = await get_user_accessible_kb_ids(db, user)

    statement = db.execute.await_args.args[0]
    compiled = str(statement.compile(compile_kwargs={"literal_binds": True}))
    assert "knowledge_bases.status = 'active'" in compiled
    assert result == {"kb-active"}


@pytest.mark.asyncio
async def test_regular_user_cannot_list_archived_knowledge_bases() -> None:
    db = SimpleNamespace(
        execute=AsyncMock(
            side_effect=[
                _Rows(),
                _DepartmentAdmin(),
                _KnowledgeRows(),
            ]
        )
    )
    user = SimpleNamespace(id="user-1", department_id="department-1", roles=[])

    items, total = await knowledge_service.list_knowledge_bases(
        db,
        user,
        page=1,
        page_size=20,
    )

    statement = db.execute.await_args.args[0]
    compiled = str(statement.compile(compile_kwargs={"literal_binds": True}))
    assert "knowledge_bases.status = 'active'" in compiled
    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_archived_knowledge_base_rejects_document_writes() -> None:
    knowledge_base = SimpleNamespace(id="kb-archived", status="archived")
    service = object.__new__(DocumentService)
    service.session = SimpleNamespace(get=AsyncMock(return_value=knowledge_base))

    with pytest.raises(AppException) as exc_info:
        await service._require_active_kb("kb-archived")

    assert exc_info.value.code == ErrorCode.KB_ARCHIVED
    assert exc_info.value.status_code == 409
    assert exc_info.value.message == "知识库已归档，请先恢复后再操作"
