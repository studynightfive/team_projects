"""RAG 问答结果缓存：相同用户 + 知识库 + 规范化问题优先命中缓存。"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

import structlog
from redis.asyncio import Redis

from app.common.config import settings
from app.rag.search.schemas import RagAnswerResponse, SearchHit

logger = structlog.get_logger()
CACHE_SCHEMA_VERSION = "v2-rerank"

_WHITESPACE = re.compile(r"\s+")
_THINK_BLOCK_RE = re.compile(
    r"<think\b[^>]*>.*?</think>",
    flags=re.IGNORECASE | re.DOTALL,
)


def normalize_query(query: str) -> str:
    return _WHITESPACE.sub(" ", query.strip().lower())


def _strip_think_blocks(text: str) -> str:
    return _THINK_BLOCK_RE.sub("", text).strip()


def _cache_key(*, user_id: str, kb_id: str | None, query: str) -> str:
    digest = hashlib.sha256(
        f"{CACHE_SCHEMA_VERSION}|{user_id}|{kb_id or ''}|{normalize_query(query)}".encode()
    ).hexdigest()
    return f"rag:answer_cache:{digest}"


async def _redis() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)  # type: ignore[no-any-return]


async def get_cached_answer(
    *,
    user_id: str,
    kb_id: str | None,
    query: str,
) -> RagAnswerResponse | None:
    if not settings.rag_answer_cache_enabled:
        return None
    key = _cache_key(user_id=user_id, kb_id=kb_id, query=query)
    client = await _redis()
    try:
        raw = await client.get(key)
    finally:
        await client.aclose()
    if not raw:
        return None
    try:
        payload: dict[str, Any] = json.loads(raw)
        hits = [SearchHit.model_validate(item) for item in payload.get("hits", [])]
        return RagAnswerResponse(
            answer=_strip_think_blocks(str(payload.get("answer") or "")),
            hits=hits,
            mode=payload.get("mode") or "hybrid",
            took_ms=int(payload.get("took_ms") or 0),
            model=payload.get("model"),
            conversation_id=payload.get("conversation_id"),
            generated=bool(payload.get("generated", True)),
            from_cache=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("rag_answer_cache_decode_failed", error_type=type(exc).__name__)
        return None


async def set_cached_answer(
    *,
    user_id: str,
    kb_id: str | None,
    query: str,
    response: RagAnswerResponse,
) -> None:
    if not settings.rag_answer_cache_enabled:
        return
    if not response.generated or not response.answer.strip():
        return
    key = _cache_key(user_id=user_id, kb_id=kb_id, query=query)
    payload = {
        "answer": _strip_think_blocks(response.answer),
        "hits": [hit.model_dump() for hit in response.hits],
        "mode": response.mode,
        "took_ms": response.took_ms,
        "model": response.model,
        "conversation_id": response.conversation_id,
        "generated": response.generated,
    }
    client = await _redis()
    try:
        await client.set(
            key,
            json.dumps(payload, ensure_ascii=False),
            ex=settings.rag_answer_cache_ttl_seconds,
        )
    finally:
        await client.aclose()
    logger.info("rag_answer_cache_stored", kb_id=kb_id)
