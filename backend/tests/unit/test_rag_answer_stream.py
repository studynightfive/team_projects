"""无会话 RAG 流式回答测试。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.rag.answer_cache import AnswerCacheScope
from app.rag.search.schemas import (
    RagAnswerRequest,
    RagAnswerResponse,
    SearchHit,
    SearchResponse,
)
from app.rag.search.service import (
    is_no_context_answer,
    sanitize_no_context_answer,
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


def test_no_context_answer_removes_model_generated_evidence_section() -> None:
    answer = (
        "未在文档中找到关于天气的相关引用。请补充对应资料。"
        "\n\n**关键依据：**\n\n- [1] 当前文档只涉及医疗系统。"
    )

    assert is_no_context_answer(answer) is True
    assert sanitize_no_context_answer(answer) == (
        "未在文档中找到关于天气的相关引用。请补充对应资料。"
    )
    assert is_no_context_answer("文档说明系统包含电子病历模块 [1]。") is False


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
    monkeypatch.setattr(
        "app.rag.search.stream._prepare_conversation",
        AsyncMock(
            return_value=(
                SimpleNamespace(id="conversation-1"),
                SimpleNamespace(id="user-message-1"),
                [],
            )
        ),
    )
    monkeypatch.setattr(
        "app.rag.search.stream._save_assistant_message",
        AsyncMock(return_value=SimpleNamespace(id="assistant-message-1")),
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
    assert events[0].data["conversation_id"] == "conversation-1"
    assert "stage" in names
    assert "citation" in names
    assert names[-1] == "done"
    assert names.index("citation") > max(
        index for index, name in enumerate(names) if name == "delta"
    )
    visible_answer = "".join(
        str(event.data["text"]) for event in events if event.event == "delta"
    )
    assert visible_answer == "平台包含电子病历。"
    assert "不应显示" not in visible_answer
    cache_write.assert_awaited_once()
    assert events[-1].data["message_id"] == "assistant-message-1"


@pytest.mark.asyncio
async def test_stream_answer_hides_citations_when_model_reports_no_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = RagAnswerRequest(
        query="文档中没有说明的问题",
        mode="hybrid",
        kb_id="kb-1",
        chat_model_id="chat-1",
        embedding_model_id="embedding-1",
    )
    hit = SearchHit(
        doc_id="doc-1",
        chunk_id="chunk-1",
        doc_title="仅名称相似的文档",
        score=0.82,
        text="该片段与问题名称相似，但不包含答案。",
        kb_id="kb-1",
    )

    async def provider_deltas():
        yield "未在文档中找到相关信息。"
        yield "请补充更具体的业务资料后重试。"

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
    monkeypatch.setattr(
        "app.rag.search.stream._prepare_conversation",
        AsyncMock(
            return_value=(
                SimpleNamespace(id="conversation-1"),
                SimpleNamespace(id="user-message-1"),
                [],
            )
        ),
    )
    save_message = AsyncMock(return_value=SimpleNamespace(id="assistant-message-1"))
    monkeypatch.setattr(
        "app.rag.search.stream._save_assistant_message",
        save_message,
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

    assert all(event.event != "citation" for event in events)
    assert events[-1].data["generated"] is True
    save_message.assert_awaited_once_with(
        SimpleNamespace(),
        conversation_id="conversation-1",
        answer="未在文档中找到相关信息。请补充更具体的业务资料后重试。",
        hits=[],
        finish_reason="no_context",
    )
    cache_write.assert_not_awaited()


@pytest.mark.asyncio
async def test_followup_uses_history_and_skips_answer_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = RagAnswerRequest(
        query="那数据中心呢",
        mode="hybrid",
        kb_id="kb-1",
        conversation_id="conversation-1",
        chat_model_id="chat-1",
        embedding_model_id="embedding-1",
    )
    effective_request = request.model_copy(update={"kb_id": None, "kb_ids": ["kb-1"]})
    hit = SearchHit(
        doc_id="doc-1",
        chunk_id="chunk-1",
        doc_title="医疗信息化方案",
        score=0.93,
        text="数据中心负责汇聚临床与运营数据。",
        kb_id="kb-1",
    )

    async def provider_deltas():
        yield "数据中心负责统一汇聚数据。"

    provider = SimpleNamespace(chat=AsyncMock(return_value=provider_deltas()))
    existing = SimpleNamespace(
        id="conversation-1",
        kb_id="kb-1",
        knowledge_base_ids=["kb-1"],
    )
    monkeypatch.setattr(
        "app.rag.search.stream.get_conversation",
        AsyncMock(return_value=existing),
    )
    monkeypatch.setattr(
        "app.rag.search.stream._build_answer_cache_scope",
        AsyncMock(return_value=(_scope(), effective_request)),
    )
    cache_read = AsyncMock()
    monkeypatch.setattr("app.rag.search.stream.get_cached_answer", cache_read)
    monkeypatch.setattr(
        "app.rag.search.stream._prepare_conversation",
        AsyncMock(
            return_value=(
                existing,
                SimpleNamespace(id="user-message-2"),
                [
                    ("user", "医疗信息化平台有哪些模块"),
                    ("assistant", "平台包含电子病历和数据中心。"),
                ],
            )
        ),
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
    monkeypatch.setattr(
        "app.rag.search.stream._save_assistant_message",
        AsyncMock(return_value=SimpleNamespace(id="assistant-message-2")),
    )

    events = [
        event
        async for event in stream_answer(
            SimpleNamespace(),
            user=SimpleNamespace(id="user-1"),
            req=request,
        )
    ]

    cache_read.assert_not_awaited()
    cache_write.assert_not_awaited()
    messages = provider.chat.await_args.kwargs["messages"]
    assert [message["role"] for message in messages] == [
        "system",
        "user",
        "assistant",
        "user",
    ]
    assert messages[-1]["content"] == "那数据中心呢"
    assert events[-1].data["conversation_id"] == "conversation-1"


@pytest.mark.asyncio
async def test_standalone_question_in_conversation_can_reuse_semantic_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = RagAnswerRequest(
        query="医疗信息化有哪些企业在做",
        mode="hybrid",
        kb_id="kb-1",
        conversation_id="conversation-1",
        chat_model_id="chat-1",
        embedding_model_id="embedding-1",
    )
    effective_request = request.model_copy(update={"kb_id": None, "kb_ids": ["kb-1"]})
    cached = RagAnswerResponse(
        answer="知识库提到了多家医疗信息化企业。",
        hits=[
            SearchHit(
                doc_id="doc-1",
                chunk_id="chunk-1",
                doc_title="医疗信息化方案",
                score=0.93,
                text="企业相关引用。",
                kb_id="kb-1",
            )
        ],
        mode="hybrid",
        took_ms=30,
        model="deepseek-chat",
        generated=True,
        from_cache=True,
        cache_match="similar",
        cache_similarity=0.979,
    )
    existing = SimpleNamespace(
        id="conversation-1",
        kb_id="kb-1",
        knowledge_base_ids=["kb-1"],
    )
    monkeypatch.setattr(
        "app.rag.search.stream.get_conversation",
        AsyncMock(return_value=existing),
    )
    monkeypatch.setattr(
        "app.rag.search.stream._build_answer_cache_scope",
        AsyncMock(return_value=(_scope(), effective_request)),
    )
    cache_read = AsyncMock(return_value=cached)
    monkeypatch.setattr("app.rag.search.stream.get_cached_answer", cache_read)
    search_call = AsyncMock()
    monkeypatch.setattr("app.rag.search.stream.search", search_call)
    monkeypatch.setattr(
        "app.rag.search.stream._prepare_conversation",
        AsyncMock(
            return_value=(
                existing,
                SimpleNamespace(id="user-message-2"),
                [
                    ("user", "医疗信息化有企业在做"),
                    ("assistant", "知识库提到了相关企业。"),
                ],
            )
        ),
    )
    monkeypatch.setattr(
        "app.rag.search.stream._save_assistant_message",
        AsyncMock(return_value=SimpleNamespace(id="assistant-message-2")),
    )

    events = [
        event
        async for event in stream_answer(
            SimpleNamespace(),
            user=SimpleNamespace(id="user-1"),
            req=request,
        )
    ]

    cache_read.assert_awaited_once_with(scope=_scope(), query=request.query)
    search_call.assert_not_awaited()
    assert "".join(
        str(event.data["text"]) for event in events if event.event == "delta"
    ) == cached.answer
    assert events[-1].data["cache_match"] == "similar"
    assert events[-1].data["cache_similarity"] == 0.979
