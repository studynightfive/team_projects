"""Milvus 后端：无 pymilvus 时的错误信息与 pad 逻辑。"""

from __future__ import annotations

import pytest

from app.rag.vector_store.milvus import MilvusVectorStore


def test_milvus_pad_and_truncate() -> None:
    store = MilvusVectorStore()
    store.dim = 4
    assert store._pad([1.0, 2.0]) == [1.0, 2.0, 0.0, 0.0]
    assert store._pad([1.0, 2.0, 3.0, 4.0, 5.0]) == [1.0, 2.0, 3.0, 4.0]


@pytest.mark.asyncio
async def test_milvus_search_without_pymilvus_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    store = MilvusVectorStore()

    def _boom() -> None:
        raise RuntimeError("未安装 pymilvus")

    monkeypatch.setattr(store, "_ensure_collection", _boom)
    with pytest.raises(RuntimeError, match="pymilvus"):
        await store.search(embedding=[0.1] * 8, accessible_kb_ids={"k1"}, top_k=3)
