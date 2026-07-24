"""多知识库检索范围测试。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.common.exceptions import ValidationException
from app.rag.search import service as search_service
from app.rag.search.schemas import SearchRequest


class _NameResult:
    def __init__(self, names: list[str]) -> None:
        self.names = names

    def scalars(self):
        return self.names


def test_search_request_rejects_conflicting_or_duplicate_scope() -> None:
    with pytest.raises(ValidationError):
        SearchRequest(
            query="问题",
            mode="hybrid",
            kb_id="kb-1",
            kb_ids=["kb-2"],
        )
    with pytest.raises(ValidationError):
        SearchRequest(
            query="问题",
            mode="hybrid",
            kb_ids=["kb-1", "kb-1"],
        )


@pytest.mark.asyncio
async def test_search_rejects_same_name_knowledge_bases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        search_service,
        "get_user_accessible_kb_ids",
        AsyncMock(return_value={"kb-1", "kb-2"}),
    )
    db = SimpleNamespace(
        execute=AsyncMock(return_value=_NameResult(["医疗知识库", " 医疗知识库 "])),
    )

    with pytest.raises(ValidationException, match="同名知识库"):
        await search_service.search(
            db,
            user=SimpleNamespace(id="user-1"),
            req=SearchRequest(
                query="医保结算流程",
                mode="keyword",
                kb_ids=["kb-1", "kb-2"],
                rerank=False,
            ),
            guard_checked=True,
        )
