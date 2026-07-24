"""面向 AI 搜索的无会话 RAG 流式回答。"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Literal

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import settings
from app.common.models import User
from app.models.providers.openai import OpenAICompatibleProvider, build_provider
from app.rag._shared.permissions import new_request_id
from app.rag.answer_cache import get_cached_answer, set_cached_answer
from app.rag.search.schemas import RagAnswerRequest, RagAnswerResponse, SearchHit
from app.rag.search.service import (
    _build_answer_cache_scope,
    _build_answer_messages,
    _build_cache_query_embedding,
    _resolve_chat_model,
    search,
)

logger = structlog.get_logger()
StreamEventName = Literal["start", "stage", "citation", "delta", "done", "error"]


@dataclass(frozen=True)
class AnswerStreamEvent:
    event: StreamEventName
    data: dict[str, Any]


class ThinkBlockStreamFilter:
    """跨 Provider 分片过滤 `<think>`，避免隐藏推理内容泄露给客户端。"""

    _OPEN = "<think"
    _CLOSE = "</think>"

    def __init__(self) -> None:
        self._buffer = ""
        self._inside_think = False

    @staticmethod
    def _partial_prefix_length(value: str, marker: str) -> int:
        max_length = min(len(value), len(marker) - 1)
        for length in range(max_length, 0, -1):
            if marker.startswith(value[-length:].lower()):
                return length
        return 0

    def feed(self, chunk: str) -> str:
        self._buffer += chunk
        visible: list[str] = []
        while self._buffer:
            lowered = self._buffer.lower()
            if self._inside_think:
                close_index = lowered.find(self._CLOSE)
                if close_index < 0:
                    keep = self._partial_prefix_length(self._buffer, self._CLOSE)
                    self._buffer = self._buffer[-keep:] if keep else ""
                    break
                self._buffer = self._buffer[close_index + len(self._CLOSE) :]
                self._inside_think = False
                continue

            open_index = lowered.find(self._OPEN)
            if open_index < 0:
                keep = self._partial_prefix_length(self._buffer, self._OPEN)
                if keep:
                    visible.append(self._buffer[:-keep])
                    self._buffer = self._buffer[-keep:]
                else:
                    visible.append(self._buffer)
                    self._buffer = ""
                break

            visible.append(self._buffer[:open_index])
            tag_end = self._buffer.find(">", open_index)
            if tag_end < 0:
                self._buffer = self._buffer[open_index:]
                break
            self._buffer = self._buffer[tag_end + 1 :]
            self._inside_think = True
        return "".join(visible)

    def finish(self) -> str:
        if self._inside_think:
            self._buffer = ""
            return ""
        visible = self._buffer
        self._buffer = ""
        return visible


def _elapsed_ms(started_at: float) -> int:
    return int((time.monotonic() - started_at) * 1000)


def _stage(
    *,
    stage: str,
    label: str,
    status: Literal["running", "completed"],
    started_at: float,
    detail: str,
) -> AnswerStreamEvent:
    return AnswerStreamEvent(
        event="stage",
        data={
            "event": "stage",
            "stage": stage,
            "label": label,
            "status": status,
            "detail": detail,
            "elapsed_ms": _elapsed_ms(started_at),
        },
    )


def _citation_event(hit: SearchHit) -> AnswerStreamEvent:
    return AnswerStreamEvent(
        event="citation",
        data={"event": "citation", **hit.model_dump(mode="json")},
    )


def _done_event(
    response: RagAnswerResponse,
    *,
    started_at: float,
) -> AnswerStreamEvent:
    return AnswerStreamEvent(
        event="done",
        data={
            "event": "done",
            "took_ms": _elapsed_ms(started_at),
            "mode": response.mode,
            "model": response.model,
            "generated": response.generated,
            "from_cache": response.from_cache,
            "cache_match": response.cache_match,
            "cache_similarity": response.cache_similarity,
        },
    )


async def stream_answer(
    db: AsyncSession,
    *,
    user: User,
    req: RagAnswerRequest,
) -> AsyncIterator[AnswerStreamEvent]:
    started_at = time.monotonic()
    request_id = new_request_id()
    yield AnswerStreamEvent(
        event="start",
        data={"event": "start", "request_id": request_id},
    )

    yield _stage(
        stage="cache",
        label="检查可复用答案",
        status="running",
        started_at=started_at,
        detail="正在核对权限、文档版本与检索配置。",
    )
    cache_scope, effective_request = await _build_answer_cache_scope(
        db,
        user=user,
        req=req,
    )
    cached = await get_cached_answer(scope=cache_scope, query=req.query)
    query_embedding: list[float] | None = None
    if cached is None:
        query_embedding = await _build_cache_query_embedding(
            db,
            req=effective_request,
        )
        if query_embedding is not None:
            cached = await get_cached_answer(
                scope=cache_scope,
                query=req.query,
                query_embedding=query_embedding,
                check_exact=False,
            )
    if cached is not None:
        cached.took_ms = _elapsed_ms(started_at)
        yield _stage(
            stage="cache",
            label="检查可复用答案",
            status="completed",
            started_at=started_at,
            detail=(
                "已命中完全相同问题缓存。"
                if cached.cache_match == "exact"
                else "已命中高置信度相似问题缓存。"
            ),
        )
        for hit in cached.hits:
            yield _citation_event(hit)
        yield AnswerStreamEvent(
            event="delta",
            data={"event": "delta", "text": cached.answer},
        )
        yield _done_event(cached, started_at=started_at)
        return

    yield _stage(
        stage="cache",
        label="检查可复用答案",
        status="completed",
        started_at=started_at,
        detail="未命中可安全复用的答案。",
    )
    yield _stage(
        stage="retrieval",
        label="检索知识库",
        status="running",
        started_at=started_at,
        detail="正在检索当前账号有权访问的文档分块。",
    )
    search_response = await search(
        db,
        user=user,
        req=effective_request,
        guard_checked=True,
        query_embedding=query_embedding,
    )
    yield _stage(
        stage="retrieval",
        label="检索知识库",
        status="completed",
        started_at=started_at,
        detail=f"已找到 {len(search_response.hits)} 条可引用内容。",
    )
    if effective_request.rerank:
        yield _stage(
            stage="rerank",
            label="重排检索结果",
            status="completed",
            started_at=started_at,
            detail=(
                "已使用重排模型优化引用顺序。"
                if search_response.reranked
                else "重排模型不可用，已保留检索排序。"
            ),
        )
    for hit in search_response.hits:
        yield _citation_event(hit)

    if not search_response.hits:
        response = RagAnswerResponse(
            answer="未在文档中找到相关引用。请换用更贴近文档内容的关键词后重试。",
            hits=[],
            mode=search_response.mode,
            took_ms=_elapsed_ms(started_at),
            model=None,
            generated=False,
        )
        yield AnswerStreamEvent(
            event="delta",
            data={"event": "delta", "text": response.answer},
        )
        yield _done_event(response, started_at=started_at)
        return

    (
        provider_code,
        base_url,
        model_name,
        api_key,
        temperature,
        max_tokens,
    ) = await _resolve_chat_model(db, chat_model_id=req.chat_model_id)
    provider: OpenAICompatibleProvider = build_provider(
        provider_code,
        base_url,
        api_key,
        timeout=settings.model_provider_timeout_seconds,
    )
    yield _stage(
        stage="generation",
        label="生成知识库回答",
        status="running",
        started_at=started_at,
        detail=f"正在由 {model_name} 基于引用内容组织回答。",
    )
    provider_stream = await provider.chat(
        model_name=model_name,
        messages=_build_answer_messages(req.query, search_response.hits),
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
        timeout=settings.model_provider_timeout_seconds,
    )
    if isinstance(provider_stream, str):
        raise TypeError("流式模型返回了非流式结果")

    answer_parts: list[str] = []
    think_filter = ThinkBlockStreamFilter()
    async for provider_delta in provider_stream:
        visible_delta = think_filter.feed(provider_delta)
        if not visible_delta:
            continue
        answer_parts.append(visible_delta)
        yield AnswerStreamEvent(
            event="delta",
            data={"event": "delta", "text": visible_delta},
        )
    trailing_text = think_filter.finish()
    if trailing_text:
        answer_parts.append(trailing_text)
        yield AnswerStreamEvent(
            event="delta",
            data={"event": "delta", "text": trailing_text},
        )

    answer_text = "".join(answer_parts).strip()
    if not answer_text:
        answer_text = "未在文档中找到相关引用。"
        yield AnswerStreamEvent(
            event="delta",
            data={"event": "delta", "text": answer_text},
        )
    response = RagAnswerResponse(
        answer=answer_text,
        hits=search_response.hits,
        mode=search_response.mode,
        took_ms=_elapsed_ms(started_at),
        model=model_name,
        generated=True,
    )
    await set_cached_answer(
        scope=cache_scope,
        query=req.query,
        response=response,
        query_embedding=query_embedding,
    )
    yield _stage(
        stage="generation",
        label="生成知识库回答",
        status="completed",
        started_at=started_at,
        detail="回答生成完成，引用来源已保留。",
    )
    yield _done_event(response, started_at=started_at)
