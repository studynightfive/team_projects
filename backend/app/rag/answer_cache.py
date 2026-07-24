"""RAG 答案缓存：按权限、内容版本、模型与检索参数隔离精确和相似问题。"""

from __future__ import annotations

import hashlib
import json
import re
import time
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

import structlog
from redis.asyncio import Redis

from app.common.config import settings
from app.rag.search.schemas import CacheMatch, RagAnswerResponse, SearchHit

logger = structlog.get_logger()
CACHE_SCHEMA_VERSION = "v3-stream-scope"

_WHITESPACE = re.compile(r"\s+")
_WORD = re.compile(r"[a-z0-9_]+|[\u4e00-\u9fff]+")
_THINK_BLOCK_RE = re.compile(
    r"<think\b[^>]*>.*?</think>",
    flags=re.IGNORECASE | re.DOTALL,
)
_POLITE_PREFIX = re.compile(r"^(?:请问|麻烦问一下|帮我查一下|我想知道|请帮我|请说明)")
_PUNCTUATION = re.compile(r"[\W_]+", flags=re.UNICODE)


@dataclass(frozen=True)
class AnswerCacheScope:
    user_id: str
    knowledge_scope: str
    knowledge_version: str
    model_scope: str
    retrieval_scope: str

    def digest(self) -> str:
        payload = "|".join(
            (
                CACHE_SCHEMA_VERSION,
                self.user_id,
                self.knowledge_scope,
                self.knowledge_version,
                self.model_scope,
                self.retrieval_scope,
            )
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalize_query(query: str) -> str:
    normalized = unicodedata.normalize("NFKC", query).strip().lower()
    normalized = _POLITE_PREFIX.sub("", normalized)
    normalized = _PUNCTUATION.sub("", normalized)
    return _WHITESPACE.sub("", normalized)


def _query_features(query: str) -> set[str]:
    normalized = unicodedata.normalize("NFKC", query).strip().lower()
    features: set[str] = set()
    for token in _WORD.findall(normalized):
        if token.isascii():
            features.add(f"w:{token}")
            continue
        if len(token) == 1:
            features.add(f"c:{token}")
            continue
        features.update(f"c:{token[index:index + 2]}" for index in range(len(token) - 1))
    return features


def question_similarity(left: str, right: str) -> float:
    left_normalized = normalize_query(left)
    right_normalized = normalize_query(right)
    if not left_normalized or not right_normalized:
        return 0.0
    if left_normalized == right_normalized:
        return 1.0
    if min(len(left_normalized), len(right_normalized)) < 6:
        return 0.0

    sequence_score = SequenceMatcher(
        None,
        left_normalized,
        right_normalized,
        autojunk=False,
    ).ratio()
    left_features = _query_features(left)
    right_features = _query_features(right)
    union = left_features | right_features
    feature_score = len(left_features & right_features) / len(union) if union else 0.0
    length_ratio = min(len(left_normalized), len(right_normalized)) / max(
        len(left_normalized),
        len(right_normalized),
    )
    return max(sequence_score, feature_score * length_ratio)


def _strip_think_blocks(text: str) -> str:
    return _THINK_BLOCK_RE.sub("", text).strip()


def _entry_key(*, scope_digest: str, query: str) -> str:
    query_digest = hashlib.sha256(normalize_query(query).encode("utf-8")).hexdigest()
    return f"rag:answer_cache:{scope_digest}:{query_digest}"


def _index_key(scope_digest: str) -> str:
    return f"rag:answer_cache_index:{scope_digest}"


async def _redis() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)  # type: ignore[no-any-return]


def _decode_response(
    raw: str,
    *,
    cache_match: CacheMatch,
    similarity: float,
) -> RagAnswerResponse | None:
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
            cache_match=cache_match,
            cache_similarity=round(similarity, 4),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("rag_answer_cache_decode_failed", error_type=type(exc).__name__)
        return None


async def get_cached_answer(
    *,
    scope: AnswerCacheScope,
    query: str,
) -> RagAnswerResponse | None:
    if not settings.rag_answer_cache_enabled:
        return None

    scope_digest = scope.digest()
    exact_key = _entry_key(scope_digest=scope_digest, query=query)
    client = await _redis()
    try:
        raw = await client.get(exact_key)
        if raw:
            return _decode_response(raw, cache_match="exact", similarity=1.0)

        candidate_keys = await client.zrevrange(
            _index_key(scope_digest),
            0,
            settings.rag_answer_cache_candidate_limit - 1,
        )
        if not candidate_keys:
            return None
        candidate_payloads = await client.mget(candidate_keys)
        best_raw: str | None = None
        best_similarity = 0.0
        for candidate_raw in candidate_payloads:
            if not candidate_raw:
                continue
            try:
                candidate = json.loads(candidate_raw)
                candidate_query = str(candidate.get("query") or "")
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            similarity = question_similarity(query, candidate_query)
            if similarity > best_similarity:
                best_similarity = similarity
                best_raw = candidate_raw
        if (
            best_raw is not None
            and best_similarity >= settings.rag_answer_cache_similarity_threshold
        ):
            return _decode_response(
                best_raw,
                cache_match="similar",
                similarity=best_similarity,
            )
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("rag_answer_cache_read_failed", error_type=type(exc).__name__)
        return None
    finally:
        await client.aclose()


async def set_cached_answer(
    *,
    scope: AnswerCacheScope,
    query: str,
    response: RagAnswerResponse,
) -> None:
    if not settings.rag_answer_cache_enabled:
        return
    if not response.generated or not response.answer.strip():
        return

    scope_digest = scope.digest()
    key = _entry_key(scope_digest=scope_digest, query=query)
    payload = {
        "query": query,
        "answer": _strip_think_blocks(response.answer),
        "hits": [hit.model_dump(mode="json") for hit in response.hits],
        "mode": response.mode,
        "took_ms": response.took_ms,
        "model": response.model,
        "conversation_id": response.conversation_id,
        "generated": response.generated,
    }
    client = await _redis()
    try:
        pipeline = client.pipeline(transaction=False)
        pipeline.set(
            key,
            json.dumps(payload, ensure_ascii=False),
            ex=settings.rag_answer_cache_ttl_seconds,
        )
        pipeline.zadd(_index_key(scope_digest), {key: time.time()})
        pipeline.expire(
            _index_key(scope_digest),
            settings.rag_answer_cache_ttl_seconds,
        )
        pipeline.zremrangebyrank(
            _index_key(scope_digest),
            0,
            -(settings.rag_answer_cache_candidate_limit + 1),
        )
        await pipeline.execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("rag_answer_cache_write_failed", error_type=type(exc).__name__)
        return
    finally:
        await client.aclose()
    logger.info("rag_answer_cache_stored", knowledge_scope=scope.knowledge_scope)
