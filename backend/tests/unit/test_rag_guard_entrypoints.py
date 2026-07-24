"""验证所有用户问题入口都在下游处理前执行输入守卫。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request

from app.common.exceptions import ValidationException
from app.rag.chat import all as chat_module
from app.rag.conversations import all as conversation_module
from app.rag.search import service as search_service
from app.rag.search.schemas import RagAnswerRequest


def _request(path: str) -> Request:
    return Request({"type": "http", "method": "POST", "path": path, "headers": []})


async def test_answer_guard_runs_before_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    guard = AsyncMock(side_effect=ValidationException(message="blocked"))
    cache = AsyncMock()
    monkeypatch.setattr(search_service, "ensure_safe_query", guard)
    monkeypatch.setattr(search_service, "get_cached_answer", cache)

    with pytest.raises(ValidationException, match="blocked"):
        await search_service.answer(
            SimpleNamespace(),
            user=SimpleNamespace(id="user-1"),
            req=RagAnswerRequest(
                query="危险输入",
                mode="keyword",
                kb_id="kb-1",
            ),
        )

    guard.assert_awaited_once_with("危险输入")
    cache.assert_not_awaited()


async def test_answer_does_not_scan_twice_in_internal_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guard = AsyncMock()
    search = AsyncMock(
        return_value=search_service.SearchResponse(
            hits=[],
            mode="keyword",
            reranked=False,
            took_ms=1,
            total_candidates=0,
        )
    )
    monkeypatch.setattr(search_service, "ensure_safe_query", guard)
    monkeypatch.setattr(search_service, "get_cached_answer", AsyncMock(return_value=None))
    monkeypatch.setattr(
        search_service,
        "_build_answer_cache_scope",
        AsyncMock(
            return_value=(
                SimpleNamespace(),
                RagAnswerRequest(query="正常问题", mode="keyword", kb_id="kb-1"),
            )
        ),
    )
    monkeypatch.setattr(search_service, "search", search)

    await search_service.answer(
        SimpleNamespace(),
        user=SimpleNamespace(id="user-1"),
        req=RagAnswerRequest(query="正常问题", mode="keyword", kb_id="kb-1"),
    )

    guard.assert_awaited_once_with("正常问题")
    assert search.await_args.kwargs["guard_checked"] is True


async def test_chat_stream_guard_runs_before_response_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guard = AsyncMock(side_effect=ValidationException(message="blocked"))
    monkeypatch.setattr(chat_module, "ensure_safe_query", guard)

    with pytest.raises(ValidationException, match="blocked"):
        await chat_module.chat_stream_endpoint(
            request=_request("/api/v1/chat/stream"),
            payload=chat_module.ChatStreamRequest(
                kb_id="kb-1",
                question="危险输入",
                chat_model_id="chat-1",
                embedding_model_id="embedding-1",
            ),
            user=SimpleNamespace(id="user-1"),
            _perm=None,
            db=SimpleNamespace(),
        )

    guard.assert_awaited_once_with("危险输入")


async def test_conversation_first_question_is_guarded_before_database_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guard = AsyncMock(side_effect=ValidationException(message="blocked"))
    db = SimpleNamespace(get=AsyncMock())
    monkeypatch.setattr(conversation_module, "ensure_safe_query", guard)

    with pytest.raises(ValidationException, match="blocked"):
        await conversation_module.create_conversation_endpoint(
            request=_request("/api/v1/conversations"),
            payload=conversation_module.ConversationCreate(
                kb_id="kb-1",
                first_question="危险输入",
            ),
            user=SimpleNamespace(id="user-1"),
            _perm=None,
            db=db,
        )

    guard.assert_awaited_once_with("危险输入")
    db.get.assert_not_awaited()


async def test_user_message_is_guarded_before_append(monkeypatch: pytest.MonkeyPatch) -> None:
    guard = AsyncMock(side_effect=ValidationException(message="blocked"))
    append = AsyncMock()
    monkeypatch.setattr(conversation_module, "ensure_safe_query", guard)
    monkeypatch.setattr(
        conversation_module,
        "get_conversation",
        AsyncMock(return_value=SimpleNamespace(id="conversation-1")),
    )
    monkeypatch.setattr(conversation_module, "append_message", append)

    with pytest.raises(ValidationException, match="blocked"):
        await conversation_module.append_message_endpoint(
            conversation_id="conversation-1",
            request=_request("/api/v1/conversations/conversation-1/messages"),
            payload={"role": "user", "content": "危险输入"},
            user=SimpleNamespace(id="user-1"),
            _perm=None,
            db=SimpleNamespace(),
        )

    guard.assert_awaited_once_with("危险输入")
    append.assert_not_awaited()
