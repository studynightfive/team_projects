"""命中率测试集的多集合保存与部门访问边界。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.common.exceptions import NotFoundException
from app.rag.tests import all as retrieval_tests


@pytest.mark.asyncio
async def test_multiple_datasets_are_created_as_independent_records() -> None:
    db = SimpleNamespace(add=Mock())
    first = await retrieval_tests.create_dataset(
        db,
        user_id="user-1",
        payload=retrieval_tests.RetrievalTestDatasetCreate(
            name="验收测试集",
            kb_id="kb-1",
            queries=[
                retrieval_tests.RetrievalTestQuery(
                    query="问题一",
                    relevant_chunk_ids=["chunk-1"],
                )
            ],
        ),
    )
    second = await retrieval_tests.create_dataset(
        db,
        user_id="user-1",
        payload=retrieval_tests.RetrievalTestDatasetCreate(
            name="回归测试集",
            kb_id="kb-1",
            queries=[
                retrieval_tests.RetrievalTestQuery(
                    query="问题二",
                    relevant_chunk_ids=["chunk-2"],
                )
            ],
        ),
    )

    assert first is not second
    assert first.name == "验收测试集"
    assert second.name == "回归测试集"
    assert db.add.call_count == 2


@pytest.mark.asyncio
async def test_dataset_from_other_department_is_hidden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset = SimpleNamespace(id="dataset-1", kb_id="kb-other")
    db = SimpleNamespace(get=AsyncMock(return_value=dataset))
    monkeypatch.setattr(
        retrieval_tests,
        "user_can_access_kb",
        AsyncMock(return_value=False),
    )

    with pytest.raises(NotFoundException):
        await retrieval_tests.get_accessible_dataset(
            db,
            user=SimpleNamespace(id="user-1"),
            dataset_id="dataset-1",
        )
