"""检索服务（提示词 02 §四）

实现关键词 / 向量 / 混合三种检索；RRF 融合；可选 Cross-Encoder 重排；
权限 SQL JOIN 与结果后置过滤双重保证。
"""
from __future__ import annotations

import json
import time
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import settings
from app.common.models import User
from app.models.providers.openai import build_provider
from app.models.security import decrypt_api_key
from app.models.repository import Model, ModelProvider
from app.models import service as model_service
from app.rag._shared.permissions import (
    get_user_accessible_kb_ids,
    post_filter_hits,
)
from app.rag.search.schemas import (
    SearchHit,
    SearchHitPosition,
    SearchRequest,
    SearchResponse,
)

logger = structlog.get_logger()

# RRF 常数（提示词 02 §4.2）
RRF_K = 60


# ============================================================
# 工具：把 chunks 行映射成 SearchHit
# ============================================================
def _row_to_hit(row: dict, *, kb_id: str | None = None) -> SearchHit:
    return SearchHit(
        doc_id=row["doc_id"],
        chunk_id=row["chunk_id"],
        doc_title=row.get("doc_title"),
        page=row.get("page"),
        score=float(row.get("score") or 0.0),
        text=row.get("content") or "",
        kb_id=kb_id or row.get("kb_id"),
    )


# ============================================================
# 关键词检索（PostgreSQL tsvector）
# ============================================================
async def _keyword_search(
    db: AsyncSession,
    *,
    query: str,
    accessible_kb_ids: set[str],
    top_k: int,
) -> tuple[list[dict], int]:
    if not accessible_kb_ids:
        return [], 0
    kb_list = list(accessible_kb_ids)
    sql = text(
        """
        SELECT chunk_id, doc_id, page, content,
               ts_rank_cd(to_tsvector(''simple'', content), plainto_tsquery(''simple'', :q)) AS score
        FROM chunks
        WHERE kb_id = ANY(:kb_ids)
          AND to_tsvector(''simple'', content) @@ plainto_tsquery(''simple'', :q)
        ORDER BY score DESC
        LIMIT :limit
        """
    )
    res = await db.execute(sql, {"q": query, "kb_ids": kb_list, "limit": top_k * 2})
    rows = [dict(r._mapping) for r in res.fetchall()]
    for row in rows:
        row.setdefault("kb_id", None)
    return rows, len(rows)


# ============================================================
# 向量检索（pgvector cosine）
# ============================================================
async def _embed_query(
    db: AsyncSession, *, query: str, embedding_model_id: str
) -> list[float]:
    model = await model_service.get_model(db, embedding_model_id)
    if model is None or model.kind != "embedding":
        raise ValueError("embedding model not found")
    provider = await model_service.get_provider(db, model.provider_code)
    if provider is None:
        raise ValueError("provider not found")
    api_key = decrypt_api_key(model.api_key_encrypted) if model.api_key_encrypted else ""
    p = build_provider(provider.code, provider.base_url, api_key)
    out = await p.embed(model_name=model.model_name, inputs=[query])
    return out[0]


async def _vector_search(
    db: AsyncSession,
    *,
    embedding: list[float],
    accessible_kb_ids: set[str],
    top_k: int,
) -> tuple[list[dict], int]:
    if not accessible_kb_ids:
        return [], 0
    kb_list = list(accessible_kb_ids)
    sql = text(
        """
        SELECT chunk_id, doc_id, page, content,
               1 - (embedding <=> :emb) AS score
        FROM chunks
        WHERE kb_id = ANY(:kb_ids)
          AND embedding IS NOT NULL
        ORDER BY embedding <=> :emb
        LIMIT :limit
        """
    )
    res = await db.execute(sql, {"emb": embedding, "kb_ids": kb_list, "limit": top_k * 2})
    rows = [dict(r._mapping) for r in res.fetchall()]
    for row in rows:
        row.setdefault("kb_id", None)
    return rows, len(rows)


# ============================================================
# RRF 融合
# ============================================================
def rrf_fuse(
    *,
    keyword_hits: list[dict],
    vector_hits: list[dict],
    k: int = RRF_K,
) -> list[dict]:
    """Reciprocal Rank Fusion：rrf(d) = Σ 1 / (k + rank_i(d))"""
    scores: dict[str, float] = {}
    by_chunk: dict[str, dict] = {}
    for rank, hit in enumerate(keyword_hits, start=1):
        cid = hit["chunk_id"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
        by_chunk.setdefault(cid, hit)
        by_chunk[cid]["keyword_score"] = hit.get("score")
    for rank, hit in enumerate(vector_hits, start=1):
        cid = hit["chunk_id"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
        by_chunk.setdefault(cid, hit)
        by_chunk[cid]["vector_score"] = hit.get("score")
    fused = []
    for cid, score in sorted(scores.items(), key=lambda x: -x[1]):
        hit = dict(by_chunk[cid])
        hit["score"] = score
        fused.append(hit)
    return fused


# ============================================================
# 重排
# ============================================================
async def _rerank(
    db: AsyncSession,
    *,
    query: str,
    candidates: list[dict],
    rerank_model_id: str | None,
    top_k: int,
) -> list[dict]:
    if not rerank_model_id or not candidates:
        return candidates[:top_k]
    model = await model_service.get_model(db, rerank_model_id)
    if model is None or model.kind != "rerank":
        return candidates[:top_k]
    provider = await model_service.get_provider(db, model.provider_code)
    if provider is None:
        return candidates[:top_k]
    api_key = decrypt_api_key(model.api_key_encrypted) if model.api_key_encrypted else ""
    p = build_provider(provider.code, provider.base_url, api_key)
    docs = [c.get("text") or c.get("content") or "" for c in candidates]
    try:
        results = await p.rerank(model_name=model.model_name, query=query, documents=docs, top_n=top_k)
    except Exception as exc:
        logger.warning("rerank_failed_fallback_to_rrf", error=str(exc))
        return candidates[:top_k]
    out = []
    for item in results:
        idx = item.get("index")
        if idx is None or idx >= len(candidates):
            continue
        hit = dict(candidates[idx])
        hit["rerank_score"] = float(item.get("relevance_score") or 0.0)
        hit["score"] = hit["rerank_score"]
        out.append(hit)
    return out


# ============================================================
# 统一入口
# ============================================================
async def search(
    db: AsyncSession,
    *,
    user: User,
    req: SearchRequest,
) -> SearchResponse:
    start = time.time()
    accessible = await get_user_accessible_kb_ids(db, user)
    if req.kb_id and req.kb_id not in accessible:
        # 用户显式指定了无权 kb：直接空响应，不暴露存在性
        return SearchResponse(hits=[], mode=req.mode, reranked=False, took_ms=0, total_candidates=0)
    accessible_kbs = {req.kb_id} if req.kb_id else accessible

    debug_kt, debug_vt, debug_rt = 0, 0, 0

    if req.mode == "keyword":
        ts = time.time()
        kw_hits, total = await _keyword_search(db, query=req.query, accessible_kb_ids=accessible_kbs, top_k=req.top_k)
        debug_kt = int((time.time() - ts) * 1000)
        fused = kw_hits
    elif req.mode == "vector":
        if not req.embedding_model_id:
            raise ValueError("embedding_model_id required for vector search")
        ts = time.time()
        emb = await _embed_query(db, query=req.query, embedding_model_id=req.embedding_model_id)
        debug_vt = int((time.time() - ts) * 1000)
        vec_hits, total = await _vector_search(db, embedding=emb, accessible_kb_ids=accessible_kbs, top_k=req.top_k)
        fused = vec_hits
    else:  # hybrid
        if not req.embedding_model_id:
            raise ValueError("embedding_model_id required for hybrid search")
        ts = time.time()
        kw_hits, _ = await _keyword_search(db, query=req.query, accessible_kb_ids=accessible_kbs, top_k=req.top_k)
        debug_kt = int((time.time() - ts) * 1000)
        ts = time.time()
        emb = await _embed_query(db, query=req.query, embedding_model_id=req.embedding_model_id)
        debug_vt = int((time.time() - ts) * 1000)
        vec_hits, _ = await _vector_search(db, embedding=emb, accessible_kb_ids=accessible_kbs, top_k=req.top_k)
        fused = rrf_fuse(keyword_hits=kw_hits, vector_hits=vec_hits)

    # 阈值过滤
    if req.threshold > 0:
        fused = [h for h in fused if (h.get("score") or 0.0) >= req.threshold]

    # 重排（仅当 top_k > settings.rag_max_top_k 强制启用）
    forced_rerank = req.top_k > settings.rag_max_top_k
    do_rerank = (req.rerank or forced_rerank) and req.mode != "keyword"  # keyword 不重排
    reranked = False
    if do_rerank:
        ts = time.time()
        fused = await _rerank(
            db, query=req.query, candidates=fused,
            rerank_model_id=req.rerank_model_id, top_k=req.top_k,
        )
        debug_rt = int((time.time() - ts) * 1000)
        reranked = True
    else:
        fused = fused[: req.top_k]

    # 结果后置权限过滤
    safe = post_filter_hits(hits=fused, accessible_kb_ids=accessible_kbs)
    hits = [_row_to_hit(h).model_dump() for h in safe]

    took_ms = int((time.time() - start) * 1000)
    return SearchResponse(
        hits=[SearchHit(**h) for h in hits],
        mode=req.mode,
        reranked=reranked,
        took_ms=took_ms,
        total_candidates=total,
        debug={"embedding_latency_ms": debug_vt or None,
               "keyword_latency_ms": debug_kt or None,
               "rerank_latency_ms": debug_rt or None},
    )