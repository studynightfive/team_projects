"""RAG 默认重排与真实评测回归测试。"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.common.models import User
from app.rag.search.schemas import SearchResponse
from app.rag.search.service import _resolve_embedding_model_id, _resolve_rerank_model_id
from app.rag.tests.all import (
    RetrievalTestConfig,
    _run_evaluation,
)


@pytest.mark.asyncio
async def test_default_rerank_model_uses_enabled_configured_model() -> None:
    configured = SimpleNamespace(
        id="rerank-configured",
        enabled=True,
        api_key_encrypted="encrypted-key",
    )
    disabled = SimpleNamespace(
        id="rerank-disabled",
        enabled=False,
        api_key_encrypted="encrypted-key",
    )
    db = AsyncMock()

    with patch(
        "app.rag.search.service.model_service.list_models",
        new=AsyncMock(return_value=[disabled, configured]),
    ):
        result = await _resolve_rerank_model_id(db, None)

    assert result == "rerank-configured"


@pytest.mark.asyncio
async def test_default_embedding_model_prefers_environment_model(monkeypatch) -> None:
    other = SimpleNamespace(
        id="embedding-other",
        model_name="qwen3.7-text-embedding",
        dimensions=1536,
        enabled=True,
        api_key_encrypted="encrypted-key",
    )
    configured = SimpleNamespace(
        id="embedding-configured",
        model_name="text-embedding-v2",
        dimensions=1536,
        enabled=True,
        api_key_encrypted="encrypted-key",
    )
    db = AsyncMock()
    monkeypatch.setattr(
        "app.rag.search.service.settings.qwen_embedding_model",
        "text-embedding-v2",
    )
    monkeypatch.setattr(
        "app.rag.search.service.settings.qwen_embedding_dimensions",
        1536,
    )

    with patch(
        "app.rag.search.service.model_service.list_models",
        new=AsyncMock(return_value=[other, configured]),
    ):
        result = await _resolve_embedding_model_id(db, None)

    assert result == "embedding-configured"


@pytest.mark.asyncio
async def test_repeated_evaluation_runs_real_search_each_time() -> None:
    db = AsyncMock()
    db.add = Mock()
    dataset = SimpleNamespace(
        id="dataset-1",
        kb_id="kb-1",
        queries=[
            {
                "query": "医疗信息系统如何保障数据安全？",
                "relevant_chunk_ids": ["chunk-1"],
            }
        ],
    )
    config = RetrievalTestConfig(
        mode="hybrid",
        top_k=5,
        rerank=True,
    )
    user = User(id="user-1", username="tester", display_name="测试员")
    search_mock = AsyncMock(
        return_value=SearchResponse(
            hits=[],
            mode="hybrid",
            reranked=True,
            took_ms=12,
            total_candidates=0,
        )
    )

    with (
        patch("app.rag.tests.all.search_service.search", new=search_mock),
        patch(
            "app.rag.tests.all._resolve_relevant_chunk_ids",
            new=AsyncMock(return_value=["chunk-1"]),
        ),
    ):
        await _run_evaluation(db, user=user, dataset=dataset, config=config)
        await _run_evaluation(db, user=user, dataset=dataset, config=config)

    assert search_mock.await_count == 2
