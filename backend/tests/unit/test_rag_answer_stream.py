"""无会话 RAG 流式回答测试。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.rag.answer_cache import AnswerCacheScope
from app.rag.search.schemas import (
    RagAnswerRequest,
    SearchHit,
    SearchResponse,
)
from app.rag.search.stream import ThinkBlockStreamFilter, stream_answer


def _scope() -> AnswerCacheScope:
    return AnswerCacheScope(
        user_id="user-1",
        knowledge_scope="kb-1",
        knowledge_version="version-1",
        model_scope="models",
        retrieval_scope="retrieval",
    )


def test_think_filter_handles_split_tags() -> None:
    stream_filter = ThinkBlockStreamFilter()

    visible = "".join(
        (
            stream_filter.feed("回答开头<th"),
            stream_filter.feed("ink>隐藏推理"),
            stream_filter.feed("</thi"),
            stream_filter.feed("nk>回答结尾"),
            stream_filter.finish(),
        )
    )

    assert visible == "回答开头回答结尾"
    assert "隐藏推理" not in visible


@pytest.mark.asyncio
async def test_stream_answer_emits_stages_citations_and_filtered_deltas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = RagAnswerRequest(
        query="医疗信息化平台有哪些模块",
        mode="hybrid",
        kb_id="kb-1",
        chat_model_id="chat-1",
        embedding_model_id="embedding-1",
        rerank_model_id="rerank-1",
    )
    hit = SearchHit(
        doc_id="doc-1",
        chunk_id="chunk-1",
        doc_title="医疗信息化方案",
        score=0.95,
        text="平台包含电子病历和数据中心。",
        kb_id="kb-1",
    )

    async def provider_deltas():
        for delta in ("平台包含", "<think>不应显示</think>", "电子病历。"):
            yield delta

    provider = SimpleNamespace(chat=AsyncMock(return_value=provider_deltas()))
    monkeypatch.setattr(
        "app.rag.search.stream._build_answer_cache_scope",
        AsyncMock(return_value=(_scope(), request)),
    )
    monkeypatch.setattr(
        "app.rag.search.stream.get_cached_answer",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "app.rag.search.stream.search",
        AsyncMock(
            return_value=SearchResponse(
                hits=[hit],
                mode="hybrid",
                reranked=True,
                took_ms=20,
                total_candidates=1,
            )
        ),
    )
    monkeypatch.setattr(
        "app.rag.search.stream._resolve_chat_model",
        AsyncMock(
            return_value=(
                "deepseek",
                "https://api.deepseek.com",
                "deepseek-chat",
                "secret",
                0.2,
                1200,
            )
        ),
    )
    monkeypatch.setattr(
        "app.rag.search.stream.build_provider",
        lambda *_args, **_kwargs: provider,
    )
    cache_write = AsyncMock()
    monkeypatch.setattr("app.rag.search.stream.set_cached_answer", cache_write)

    events = [
        event
        async for event in stream_answer(
            SimpleNamespace(),
            user=SimpleNamespace(id="user-1"),
            req=request,
        )
    ]

    names = [event.event for event in events]
    assert names[0] == "start"
    assert "stage" in names
    assert "citation" in names
    assert names[-1] == "done"
    visible_answer = "".join(
        str(event.data["text"]) for event in events if event.event == "delta"
    )
    assert visible_answer == "平台包含电子病历。"
    assert "不应显示" not in visible_answer
    cache_write.assert_awaited_once()
