"""真实 embedding 路径单测（mock Provider，不打外网）。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.documents.indexing import deterministic_embedding
from app.rag.embeddings import (
    LOCAL_EMBEDDING_MODEL_ID,
    embed_texts,
    is_local_embedding,
    resolve_indexing_model_id,
)


@pytest.mark.asyncio
async def test_embed_texts_local_matches_deterministic() -> None:
    db = AsyncMock()
    texts = ["alpha", "beta"]
    out = await embed_texts(db, texts, embedding_model_id=LOCAL_EMBEDDING_MODEL_ID)
    assert len(out) == 2
    assert out[0] == deterministic_embedding("alpha", 8)
    assert out[1] == deterministic_embedding("beta", 8)


@pytest.mark.asyncio
async def test_embed_texts_provider_batches() -> None:
    db = AsyncMock()
    model = SimpleNamespace(
        id="m1",
        kind="embedding",
        enabled=True,
        provider_code="openai",
        model_name="text-embedding-3-small",
        api_key_encrypted=None,
        dimensions=4,
    )
    provider = SimpleNamespace(code="openai", base_url="http://example.test", enabled=True)
    fake_p = MagicMock()
    fake_p.embed = AsyncMock(
        side_effect=[
            [[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]],
        ]
    )

    with (
        patch("app.rag.embeddings.model_service.get_model", AsyncMock(return_value=model)),
        patch("app.rag.embeddings.model_service.get_provider", AsyncMock(return_value=provider)),
        patch("app.rag.embeddings.build_provider", return_value=fake_p),
        patch("app.rag.embeddings.settings.model_api_key", "sk-test"),
    ):
        out = await embed_texts(db, ["a", "b"], embedding_model_id="m1")

    assert out == [[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]]
    fake_p.embed.assert_awaited_once()
    assert fake_p.embed.await_args.kwargs["model_name"] == "text-embedding-3-small"


def test_resolve_indexing_model_id_prefers_explicit() -> None:
    assert resolve_indexing_model_id("custom") == "custom"
    assert is_local_embedding(resolve_indexing_model_id("local"))
