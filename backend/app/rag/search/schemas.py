"""检索 Pydantic schemas（提示词 02 §三）"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

SearchMode = Literal["keyword", "vector", "hybrid"]
CacheMatch = Literal["exact", "similar"]


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    mode: SearchMode
    kb_id: str | None = None
    top_k: int = Field(default=10, ge=1, le=50)
    threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata_filter: dict[str, Any] | None = None
    rerank: bool = True
    rerank_model_id: str | None = None
    embedding_model_id: str | None = None


class SearchHitPosition(BaseModel):
    start: int | None = None
    end: int | None = None


class SearchHit(BaseModel):
    doc_id: str
    chunk_id: str
    doc_title: str | None = None
    page: int | None = None
    score: float
    vector_score: float | None = None
    keyword_score: float | None = None
    rerank_score: float | None = None
    text: str
    highlights: list[str] | None = None
    position: SearchHitPosition | None = None
    kb_id: str | None = None


class SearchDebug(BaseModel):
    embedding_latency_ms: int | None = None
    keyword_latency_ms: int | None = None
    rerank_latency_ms: int | None = None


class SearchResponse(BaseModel):
    hits: list[SearchHit]
    mode: SearchMode
    reranked: bool
    took_ms: int
    total_candidates: int
    debug: SearchDebug | None = None


class RagAnswerRequest(SearchRequest):
    chat_model_id: str | None = None


class RagAnswerResponse(BaseModel):
    answer: str
    hits: list[SearchHit]
    mode: SearchMode
    took_ms: int
    model: str | None = None
    conversation_id: str | None = None
    generated: bool = True
    from_cache: bool = False
    cache_match: CacheMatch | None = None
    cache_similarity: float | None = Field(default=None, ge=0.0, le=1.0)
