"""RAG 答案缓存：按权限、内容版本、模型与检索参数隔离精确和相似问题。"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
import unicodedata
from dataclasses import dataclass
from typing import Any

import structlog
from redis.asyncio import Redis

from app.common.config import settings
from app.rag.search.schemas import CacheMatch, RagAnswerResponse, SearchHit

logger = structlog.get_logger()
CACHE_SCHEMA_VERSION = "v4-semantic-cache"

_WHITESPACE = re.compile(r"\s+")
_THINK_BLOCK_RE = re.compile(
    r"<think\b[^>]*>.*?</think>",
    flags=re.IGNORECASE | re.DOTALL,
)
_POLITE_PREFIX = re.compile(r"^(?:请问|麻烦问一下|帮我查一下|我想知道|请帮我|请说明)")
_PUNCTUATION = re.compile(r"[\W_]+", flags=re.UNICODE)
_NUMBER = re.compile(r"\d+(?:\.\d+)?%?")
_LATIN_ENTITY = re.compile(r"[a-z][a-z0-9._-]*")
_NEGATION = re.compile(
    r"(?:不能|不可|不允许|不需要|不应|不得|没有|尚未|未能|未曾|无需|禁止|"
    r"不(?:支持|包含|包括|可以|需要|具备|存在|能够|会|是|有)|"
    r"\b(?:not|no|without|cannot|can't|mustn't)\b)",
    flags=re.IGNORECASE,
)
_LATIN_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "can",
    "do",
    "does",
    "for",
    "how",
    "in",
    "is",
    "of",
    "or",
    "the",
    "to",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
}


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


def semantic_similarity(left: list[float], right: list[float]) -> float:
    if not left or len(left) != len(right):
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return max(0.0, min(1.0, numerator / (left_norm * right_norm)))


def _question_type(query: str) -> str:
    normalized = unicodedata.normalize("NFKC", query).strip().lower()
    rules = (
        ("why", ("为什么", "为何", "原因", "why")),
        ("how", ("如何", "怎么", "怎样", "how")),
        ("quantity", ("多少", "几个", "几项", "数量", "how many")),
        ("when", ("何时", "什么时候", "多久", "when")),
        ("where", ("哪里", "何处", "在哪", "where")),
        ("who", ("谁", "哪位", "who")),
        ("yes_no", ("是否", "能否", "可否", "有没有", "是不是", "can ", "is ")),
        ("what", ("什么", "哪些", "哪种", "what", "which")),
    )
    for question_type, markers in rules:
        if any(marker in normalized for marker in markers):
            return question_type
    return "unknown"


def query_intent_features(query: str) -> dict[str, object]:
    normalized = unicodedata.normalize("NFKC", query).strip().lower()
    latin_entities = sorted(
        {token for token in _LATIN_ENTITY.findall(normalized) if token not in _LATIN_STOPWORDS}
    )
    return {
        "question_type": _question_type(normalized),
        "negated": bool(_NEGATION.search(normalized)),
        "numbers": sorted(set(_NUMBER.findall(normalized))),
        "latin_entities": latin_entities,
    }


def intents_are_compatible(left: str, right: str) -> bool:
    left_features = query_intent_features(left)
    right_features = query_intent_features(right)
    left_type = left_features["question_type"]
    right_type = right_features["question_type"]
    if left_type != "unknown" and right_type != "unknown" and left_type != right_type:
        return False
    if left_features["negated"] != right_features["negated"]:
        return False
    if left_features["numbers"] != right_features["numbers"]:
        return False
    return left_features["latin_entities"] == right_features["latin_entities"]


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
    query_embedding: list[float] | None = None,
    check_exact: bool = True,
) -> RagAnswerResponse | None:
    if not settings.rag_answer_cache_enabled:
        return None

    scope_digest = scope.digest()
    exact_key = _entry_key(scope_digest=scope_digest, query=query)
    client = await _redis()
    try:
        if check_exact:
            raw = await client.get(exact_key)
            if raw:
                return _decode_response(raw, cache_match="exact", similarity=1.0)
        if query_embedding is None:
            return None

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
                candidate_embedding = candidate.get("query_embedding")
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            if (
                not isinstance(candidate_embedding, list)
                or not all(
                    isinstance(value, int | float) and not isinstance(value, bool)
                    for value in candidate_embedding
                )
                or not intents_are_compatible(query, candidate_query)
            ):
                continue
            similarity = semantic_similarity(
                query_embedding,
                [float(value) for value in candidate_embedding],
            )
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
    query_embedding: list[float] | None = None,
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
        "query_embedding": query_embedding,
        "query_intent": query_intent_features(query),
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
