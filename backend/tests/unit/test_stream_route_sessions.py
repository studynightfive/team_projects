"""流式路由必须在生成器内部持有独立数据库会话。"""

from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request

from app.rag.chat import all as chat_api
from app.rag.search import api as search_api
from app.rag.search.schemas import RagAnswerRequest
from app.rag.search.stream import AnswerStreamEvent


def _request(path: str) -> Request:
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": path,
            "headers": [],
            "client": ("127.0.0.1", 5000),
        }
    )
    request.state.request_id = "request-1"
    return request


@pytest.mark.asyncio
async def test_retrieval_stream_owns_session_until_done(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lifecycle: list[str] = []
    db = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())
    stream_user = SimpleNamespace(id="user-1", department_id="department-1")

    @asynccontextmanager
    async def fake_stream_session(user_id: str):
        assert user_id == "user-1"
        lifecycle.append("opened")
        yield db, stream_user
        lifecycle.append("closed")

    async def fake_stream_answer(stream_db, *, user, req):
        assert stream_db is db
        assert user is stream_user
        assert lifecycle == ["opened"]
        yield AnswerStreamEvent(
            event="start",
            data={"event": "start", "request_id": "request-1"},
        )
        yield AnswerStreamEvent(
            event="citation",
            data={
                "event": "citation",
                "doc_id": "product-1",
                "doc_title": "智能门店终端 Pro",
            },
        )
        yield AnswerStreamEvent(
            event="done",
            data={
                "event": "done",
                "generated": True,
                "from_cache": False,
                "took_ms": 10,
            },
        )

    monkeypatch.setattr(search_api, "stream_user_session", fake_stream_session)
    monkeypatch.setattr(search_api, "stream_answer", fake_stream_answer)
    metric_mock = AsyncMock()
    monkeypatch.setattr(search_api, "record_retrieval_metric", metric_mock)
    monkeypatch.setattr(search_api, "audit", AsyncMock())
    monkeypatch.setattr(search_api, "ensure_safe_query", AsyncMock())

    response = await search_api.answer_stream_endpoint(
        _request("/api/v1/retrieval/answer/stream"),
        RagAnswerRequest(query="医疗平台包含哪些模块", mode="hybrid", kb_id="kb-1"),
        SimpleNamespace(id="user-1"),
        None,
    )
    chunks = [chunk async for chunk in response.body_iterator]

    assert lifecycle == ["opened", "closed"]
    assert any("event: done" in str(chunk) for chunk in chunks)
    assert metric_mock.await_args.kwargs["primary_product_id"] == "product-1"
    assert (
        metric_mock.await_args.kwargs["primary_product_name"]
        == "智能门店终端 Pro"
    )
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_chat_stream_uses_same_session_lifetime_rule(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lifecycle: list[str] = []
    db = SimpleNamespace(rollback=AsyncMock())
    stream_user = SimpleNamespace(id="user-1")

    @asynccontextmanager
    async def fake_stream_session(user_id: str):
        assert user_id == "user-1"
        lifecycle.append("opened")
        yield db, stream_user
        lifecycle.append("closed")

    async def fake_chat_stream(stream_db, *, user, req):
        assert stream_db is db
        assert user is stream_user
        assert lifecycle == ["opened"]
        yield "event: done\ndata: {\"event\":\"done\"}\n\n"

    monkeypatch.setattr(chat_api, "stream_user_session", fake_stream_session)
    monkeypatch.setattr(chat_api, "_chat_stream", fake_chat_stream)
    monkeypatch.setattr(chat_api, "ensure_safe_query", AsyncMock())

    response = await chat_api.chat_stream_endpoint(
        _request("/api/v1/chat/stream"),
        chat_api.ChatStreamRequest(
            kb_id="kb-1",
            question="医疗平台包含哪些模块",
            chat_model_id="chat-1",
            embedding_model_id="embedding-1",
        ),
        SimpleNamespace(id="user-1"),
        None,
    )
    chunks = [chunk async for chunk in response.body_iterator]

    assert lifecycle == ["opened", "closed"]
    assert any("event: done" in str(chunk) for chunk in chunks)
