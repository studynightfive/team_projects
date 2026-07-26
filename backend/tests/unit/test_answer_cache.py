"""RAG 精确与相似答案缓存测试。"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.rag.answer_cache import (
    AnswerCacheScope,
    get_cached_answer,
    intents_are_compatible,
    normalize_query,
    semantic_similarity,
)
from app.rag.search.schemas import RagAnswerResponse, SearchHit


def _scope(*, knowledge_version: str = "version-1") -> AnswerCacheScope:
    return AnswerCacheScope(
        user_id="user-1",
        knowledge_scope="kb-1",
        knowledge_version=knowledge_version,
        model_scope="chat-1|embedding-1|rerank-1",
        retrieval_scope="hybrid|10|0",
    )


def _payload(query: str, embedding: list[float] | None = None) -> str:
    response = RagAnswerResponse(
        answer="依据知识库生成的回答。",
        hits=[
            SearchHit(
                doc_id="doc-1",
                chunk_id="chunk-1",
                score=0.9,
                text="可引用内容",
                kb_id="kb-1",
            )
        ],
        mode="hybrid",
        took_ms=120,
        model="deepseek-chat",
    )
    return json.dumps(
        {
            "query": query,
            "answer": response.answer,
            "hits": [hit.model_dump(mode="json") for hit in response.hits],
            "mode": response.mode,
            "took_ms": response.took_ms,
            "model": response.model,
            "generated": True,
            "query_embedding": embedding,
        },
        ensure_ascii=False,
    )


class _FakeRedis:
    def __init__(
        self,
        *,
        exact: str | None = None,
        candidates: list[str] | None = None,
    ) -> None:
        self.exact = exact
        self.candidates = candidates or []
        self.closed = False

    async def get(self, _key: str) -> str | None:
        return self.exact

    async def zrevrange(self, _key: str, _start: int, _end: int) -> list[str]:
        return [f"candidate-{index}" for index in range(len(self.candidates))]

    async def mget(self, _keys: list[str]) -> list[str]:
        return self.candidates

    async def aclose(self) -> None:
        self.closed = True


def test_normalize_query_removes_polite_prefix_and_punctuation() -> None:
    assert normalize_query("请问：医保结算流程是什么？") == "医保结算流程是什么"


def test_semantic_similarity_uses_cosine_score() -> None:
    assert semantic_similarity([1.0, 0.0], [0.99, 0.1]) > 0.99
    assert semantic_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_intent_guard_rejects_negation_and_entity_changes() -> None:
    assert intents_are_compatible(
        "医疗信息化平台包含哪些模块",
        "医院信息系统由哪些部分组成",
    )
    assert not intents_are_compatible(
        "医保结算允许撤销吗",
        "医保结算不允许撤销吗",
    )
    assert not intents_are_compatible(
        "HIS 系统如何部署",
        "EMR 系统如何部署",
    )


def test_scope_digest_changes_with_knowledge_version() -> None:
    assert _scope(knowledge_version="v1").digest() != _scope(knowledge_version="v2").digest()


@pytest.mark.asyncio
async def test_exact_cache_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeRedis(exact=_payload("医保结算流程是什么"))
    monkeypatch.setattr(
        "app.rag.answer_cache._redis",
        AsyncMock(return_value=client),
    )

    result = await get_cached_answer(
        scope=_scope(),
        query="医保结算流程是什么？",
    )

    assert result is not None
    assert result.cache_match == "exact"
    assert result.cache_similarity == 1.0
    assert client.closed is True


@pytest.mark.asyncio
async def test_similar_cache_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeRedis(
        candidates=[
            _payload(
                "医院信息化平台由哪些核心部分组成",
                [0.99, 0.1, 0.0],
            ),
            _payload("完全无关的教育系统问题", [0.0, 0.0, 1.0]),
        ]
    )
    monkeypatch.setattr(
        "app.rag.answer_cache._redis",
        AsyncMock(return_value=client),
    )
    monkeypatch.setattr(
        "app.rag.answer_cache.settings.rag_answer_cache_similarity_threshold",
        0.9,
    )

    result = await get_cached_answer(
        scope=_scope(),
        query="医疗信息化平台建设包含哪些核心模块？",
        query_embedding=[1.0, 0.0, 0.0],
    )

    assert result is not None
    assert result.cache_match == "similar"
    assert result.cache_similarity is not None
    assert result.cache_similarity > 0.99


@pytest.mark.asyncio
async def test_semantic_cache_rejects_opposite_intent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeRedis(
        candidates=[
            _payload("医保结算不允许撤销吗", [1.0, 0.0]),
        ]
    )
    monkeypatch.setattr(
        "app.rag.answer_cache._redis",
        AsyncMock(return_value=client),
    )

    result = await get_cached_answer(
        scope=_scope(),
        query="医保结算允许撤销吗",
        query_embedding=[1.0, 0.0],
    )

    assert result is None


@pytest.mark.asyncio
async def test_cache_failure_degrades_to_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    client = SimpleNamespace(
        get=AsyncMock(side_effect=ConnectionError("redis unavailable")),
        aclose=AsyncMock(),
    )
    monkeypatch.setattr(
        "app.rag.answer_cache._redis",
        AsyncMock(return_value=client),
    )

    result = await get_cached_answer(scope=_scope(), query="正常问题")

    assert result is None
    client.aclose.assert_awaited_once()
