"""检索服务（提示词 02 §四）

实现关键词 / 向量 / 混合三种检索；RRF 融合；可选 Cross-Encoder 重排；
权限 SQL JOIN 与结果后置过滤双重保证。
"""

from __future__ import annotations

import re
import time
from typing import TypeAlias

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import settings
from app.common.exceptions import ValidationException
from app.common.models import User
from app.models import service as model_service
from app.models.providers.openai import OpenAICompatibleProvider, build_provider
from app.models.security import decrypt_api_key
from app.rag._shared.permissions import (
    get_user_accessible_kb_ids,
    post_filter_hits,
)
from app.rag.answer_cache import get_cached_answer, set_cached_answer
from app.rag.guard import ensure_safe_query
from app.rag.search.schemas import (
    RagAnswerRequest,
    RagAnswerResponse,
    SearchDebug,
    SearchHit,
    SearchRequest,
    SearchResponse,
)

logger = structlog.get_logger()

# RRF 常数（提示词 02 §4.2）
RRF_K = 60
SearchRow: TypeAlias = dict[str, object]

def _embedding_literal(value: object) -> str:
    """序列化 embedding 为 pgvector 字面量"""
    if isinstance(value, str):
        return value
    if isinstance(value, bytes | bytearray):
        return "b'" + value.hex() + "'"
    if isinstance(value, list | tuple):
        return "[" + ",".join(str(float(x)) for x in value) + "]"
    return str(value)

def rrf_fuse_many(lists: list[list[dict[str, object]]], k: int = RRF_K) -> list[dict[str, object]]:
    """多列表 RRF 融合"""
    scores: dict[str, float] = {}
    by_chunk: dict[str, dict[str, object]] = {}
    for hits in lists:
        for rank, hit in enumerate(hits, start=1):
            cid = str(hit.get("chunk_id") or "")
            if not cid:
                continue
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
            by_chunk.setdefault(cid, hit)
    fused = []
    for cid, score in sorted(scores.items(), key=lambda x: -x[1]):
        hit = dict(by_chunk[cid])
        hit["score"] = score
        fused.append(hit)
    return fused


_CJK_STOPWORDS = {
    "的",
    "了",
    "吗",
    "呢",
    "是",
    "在",
    "有",
    "和",
    "与",
    "及",
    "或",
    "等",
    "什么",
    "怎么",
    "如何",
    "多少",
    "哪个",
    "哪些",
    "请问",
    "一下",
    "是否",
}

_THINK_BLOCK_RE = re.compile(
    r"<think\b[^>]*>.*?</think>",
    flags=re.IGNORECASE | re.DOTALL,
)


def strip_model_think_blocks(text: str) -> str:
    """去掉模型输出中的思考标签，只保留最终回答。"""
    return _THINK_BLOCK_RE.sub("", text).strip()


def extract_search_terms(query: str, *, max_terms: int = 12) -> list[str]:
    """从自然语言问题提取可检索词（支持中文连续字串拆 bigram）。"""
    cleaned = query.strip()
    if not cleaned:
        return []

    candidates: list[str] = []
    for match in re.finditer(r"[A-Za-z0-9_]{2,}", cleaned):
        candidates.append(match.group(0).lower())

    for match in re.finditer(r"[\u4e00-\u9fff]+", cleaned):
        run = match.group(0)
        if run in _CJK_STOPWORDS:
            continue
        if len(run) <= 4:
            candidates.append(run)
            continue
        for index in range(len(run) - 1):
            bigram = run[index : index + 2]
            if bigram not in _CJK_STOPWORDS:
                candidates.append(bigram)
        if len(run) <= 10:
            candidates.append(run)

    ranked = sorted(set(candidates), key=lambda item: (-len(item), item))
    terms = [item for item in ranked if len(item) >= 2][:max_terms]
    return terms if terms else [cleaned[:32]]


# ============================================================
# 工具：把 chunks 行映射成 SearchHit
# ============================================================
def _row_to_hit(row: SearchRow, *, kb_id: str | None = None) -> SearchHit:
    payload = dict(row)
    payload["score"] = row.get("score") or 0.0
    payload["text"] = row.get("content") or ""
    metadata = row.get("metadata") or {}
    if isinstance(metadata, dict):
        doc_title = metadata.get("doc_title")
        if doc_title and "doc_title" not in payload:
            payload["doc_title"] = doc_title
    if kb_id is not None:
        payload["kb_id"] = kb_id
    return SearchHit.model_validate(payload)


def _text_from_hit(hit: SearchRow) -> str:
    text_value = hit.get("text")
    content_value = text_value if isinstance(text_value, str) else hit.get("content")
    content = content_value if isinstance(content_value, str) else ""
    context = [hit.get("doc_title"), hit.get("heading"), content]
    return "\n".join(
        value.strip() for value in context if isinstance(value, str) and value.strip()
    )


def _score_from_hit(hit: SearchRow) -> float:
    value = hit.get("rerank_score", hit.get("vector_score", hit.get("score")))
    if isinstance(value, bool) or not isinstance(value, int | float):
        return 0.0
    return float(value)


def _has_retrieval_information(hit: SearchRow) -> bool:
    content = hit.get("content")
    if not isinstance(content, str):
        return False
    plain = re.sub(r"[#>*_`|\-\s\d.]+", "", content)
    return len(plain) >= 8


# ============================================================
# 关键词检索（PostgreSQL tsvector）
# ============================================================
async def _keyword_search(
    db: AsyncSession,
    *,
    query: str,
    accessible_kb_ids: set[str],
    top_k: int,
) -> tuple[list[SearchRow], int]:
    if not accessible_kb_ids:
        return [], 0
    terms = extract_search_terms(query)
    if not terms:
        return [], 0

    kb_list = list(accessible_kb_ids)
    like_clauses = " OR ".join(f"c.content ILIKE :t{i}" for i in range(len(terms)))
    score_expr = " + ".join(
        f"(CASE WHEN c.content ILIKE :t{i} THEN {max(len(terms) - i, 1)} ELSE 0 END)"
        for i in range(len(terms))
    )
    sql = text(
        f"""
        SELECT
               c.id AS chunk_id,
               c.document_id AS doc_id,
               d.title AS doc_title,
               c.knowledge_base_id AS kb_id,
               c.page_no AS page,
               c.heading AS heading,
               c.content AS content,
               ({score_expr})::float AS score
        FROM document_chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE c.knowledge_base_id = ANY(:kb_ids)
          AND c.is_active IS TRUE
          AND ({like_clauses})
        ORDER BY score DESC
        LIMIT :limit
        """
    )
    params: dict[str, object] = {
        "kb_ids": kb_list,
        "limit": top_k * 2,
    }
    for index, term in enumerate(terms):
        params[f"t{index}"] = f"%{term}%"
    res = await db.execute(sql, params)
    rows: list[SearchRow] = [dict(r._mapping) for r in res.fetchall()]
    return rows, len(rows)


# ============================================================
# 向量检索（pgvector cosine）
# ============================================================
async def _embed_query(db: AsyncSession, *, query: str, embedding_model_id: str) -> list[float]:
    model = await model_service.get_model(db, embedding_model_id)
    if model is None or model.kind != "embedding" or not model.enabled:
        raise ValueError("embedding model not found")
    provider = await model_service.get_provider(db, model.provider_code)
    if provider is None or not provider.enabled:
        raise ValueError("provider not found")
    if not model.api_key_encrypted:
        raise ValueError("embedding model api key not configured")
    api_key = decrypt_api_key(model.api_key_encrypted) if model.api_key_encrypted else ""
    p: OpenAICompatibleProvider = build_provider(provider.code, provider.base_url, api_key)
    out = await p.embed(model_name=model.model_name, inputs=[query])
    embedding = out[0]
    if len(embedding) != settings.qwen_embedding_dimensions:
        raise ValueError("embedding dimensions do not match pgvector column")
    return embedding


async def _resolve_embedding_model_id(
    db: AsyncSession,
    requested_model_id: str | None,
) -> str | None:
    if requested_model_id:
        return requested_model_id

    models = await model_service.list_models(db, kind="embedding")
    eligible = [
        model
        for model in models
        if model.enabled
        and model.api_key_encrypted
        and model.dimensions == settings.qwen_embedding_dimensions
    ]
    configured = next(
        (
            model
            for model in eligible
            if model.model_name == settings.qwen_embedding_model
        ),
        None,
    )
    return configured.id if configured is not None else (eligible[0].id if eligible else None)


def _to_vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(str(float(value)) for value in embedding) + "]"


async def _vector_search(
    db: AsyncSession,
    *,
    embedding: list[float],
    accessible_kb_ids: set[str],
    top_k: int,
) -> tuple[list[SearchRow], int]:
    if not accessible_kb_ids:
        return [], 0
    kb_list = list(accessible_kb_ids)
    sql = text(
        """
        SELECT c.id AS chunk_id,
               c.document_id AS doc_id,
               c.page_no AS page,
               c.heading AS heading,
               c.content AS content,
               d.title AS doc_title,
               c.knowledge_base_id AS kb_id,
               1 - (c.embedding_vector <=> CAST(:emb AS vector)) AS score
        FROM document_chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE c.knowledge_base_id = ANY(:kb_ids)
          AND c.is_active = TRUE
          AND c.embedding_vector IS NOT NULL
        ORDER BY c.embedding_vector <=> CAST(:emb AS vector)
        LIMIT :limit
        """
    )
    res = await db.execute(
        sql,
        {"emb": _to_vector_literal(embedding), "kb_ids": kb_list, "limit": top_k * 2},
    )
    rows: list[SearchRow] = [dict(r._mapping) for r in res.fetchall()]
    for row in rows:
        row.setdefault("kb_id", None)
    return rows, len(rows)


# ============================================================
# RRF 融合
# ============================================================
def rrf_fuse(
    *,
    keyword_hits: list[SearchRow],
    vector_hits: list[SearchRow],
    k: int = RRF_K,
) -> list[SearchRow]:
    """Reciprocal Rank Fusion：rrf(d) = Σ 1 / (k + rank_i(d))"""
    scores: dict[str, float] = {}
    by_chunk: dict[str, SearchRow] = {}
    for rank, hit in enumerate(keyword_hits, start=1):
        cid = hit.get("chunk_id")
        if not isinstance(cid, str):
            raise ValidationException(message="检索结果缺少有效的 chunk_id")
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
        by_chunk.setdefault(cid, hit)
        by_chunk[cid]["keyword_score"] = hit.get("score")
    for rank, hit in enumerate(vector_hits, start=1):
        cid = hit.get("chunk_id")
        if not isinstance(cid, str):
            raise ValidationException(message="检索结果缺少有效的 chunk_id")
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
        by_chunk.setdefault(cid, hit)
        by_chunk[cid]["vector_score"] = hit.get("score")
    fused: list[SearchRow] = []
    for cid, score in sorted(scores.items(), key=lambda x: -x[1]):
        hit = dict(by_chunk[cid])
        hit["score"] = score
        fused.append(hit)
    return fused


# ============================================================
# 重排
# ============================================================
async def _resolve_rerank_model_id(
    db: AsyncSession,
    requested_model_id: str | None,
) -> str | None:
    if requested_model_id:
        return requested_model_id

    models = await model_service.list_models(db, kind="rerank")
    configured = next(
        (
            model
            for model in models
            if model.enabled and model.api_key_encrypted
        ),
        None,
    )
    return configured.id if configured is not None else None


async def _rerank(
    db: AsyncSession,
    *,
    query: str,
    candidates: list[SearchRow],
    rerank_model_id: str | None,
    top_k: int,
) -> tuple[list[SearchRow], bool]:
    if not rerank_model_id or not candidates:
        return candidates[:top_k], False
    model = await model_service.get_model(db, rerank_model_id)
    if model is None or model.kind != "rerank" or not model.enabled:
        return candidates[:top_k], False
    provider = await model_service.get_provider(db, model.provider_code)
    if provider is None or not provider.enabled:
        return candidates[:top_k], False
    api_key = decrypt_api_key(model.api_key_encrypted) if model.api_key_encrypted else ""
    p: OpenAICompatibleProvider = build_provider(provider.code, provider.base_url, api_key)
    docs = [_text_from_hit(candidate) for candidate in candidates]
    try:
        results = await p.rerank(
            model_name=model.model_name, query=query, documents=docs, top_n=top_k
        )
    except Exception as exc:
        logger.warning(
            "rerank_failed_fallback_to_rrf",
            error_type=type(exc).__name__,
        )
        return candidates[:top_k], False
    out: list[SearchRow] = []
    for item in results:
        idx = item.get("index")
        if isinstance(idx, bool) or not isinstance(idx, int) or not 0 <= idx < len(candidates):
            continue
        hit = dict(candidates[idx])
        relevance_score = item.get("relevance_score")
        hit["rerank_score"] = (
            float(relevance_score)
            if isinstance(relevance_score, int | float) and not isinstance(relevance_score, bool)
            else 0.0
        )
        hit["score"] = hit["rerank_score"]
        out.append(hit)
    return out, True


# ============================================================
# 统一入口
# ============================================================
async def search(
    db: AsyncSession,
    *,
    user: User,
    req: SearchRequest,
    guard_checked: bool = False,
) -> SearchResponse:
    if not guard_checked:
        await ensure_safe_query(req.query)
    start = time.time()
    if req.metadata_filter:
        raise ValidationException(message="metadata_filter 尚未接入，不能静默忽略筛选条件")
    accessible = await get_user_accessible_kb_ids(db, user)
    if req.kb_id and req.kb_id not in accessible:
        # 用户显式指定了无权 kb：直接空响应，不暴露存在性
        return SearchResponse(hits=[], mode=req.mode, reranked=False, took_ms=0, total_candidates=0)
    accessible_kbs = {req.kb_id} if req.kb_id else accessible

    debug_kt, debug_vt, debug_rt = 0, 0, 0
    total = 0
    actual_mode = req.mode

    if req.mode == "keyword":
        ts = time.time()
        kw_hits, total = await _keyword_search(
            db, query=req.query, accessible_kb_ids=accessible_kbs, top_k=req.top_k
        )
        debug_kt = int((time.time() - ts) * 1000)
        fused = kw_hits
    elif req.mode == "vector":
        embedding_model_id = await _resolve_embedding_model_id(db, req.embedding_model_id)
        if not embedding_model_id:
            return SearchResponse(
                hits=[],
                mode="vector",
                reranked=False,
                took_ms=int((time.time() - start) * 1000),
                total_candidates=0,
            )
        ts = time.time()
        emb = await _embed_query(db, query=req.query, embedding_model_id=embedding_model_id)
        debug_vt = int((time.time() - ts) * 1000)
        vec_hits, total = await _vector_search(
            db, embedding=emb, accessible_kb_ids=accessible_kbs, top_k=req.top_k
        )
        fused = vec_hits
    else:  # hybrid
        ts = time.time()
        kw_hits, _ = await _keyword_search(
            db, query=req.query, accessible_kb_ids=accessible_kbs, top_k=req.top_k
        )
        debug_kt = int((time.time() - ts) * 1000)
        total = len(kw_hits)
        embedding_model_id = await _resolve_embedding_model_id(db, req.embedding_model_id)
        if embedding_model_id is None:
            actual_mode = "keyword"
            fused = kw_hits
        else:
            try:
                ts = time.time()
                emb = await _embed_query(db, query=req.query, embedding_model_id=embedding_model_id)
                debug_vt = int((time.time() - ts) * 1000)
                vec_hits, _ = await _vector_search(
                    db, embedding=emb, accessible_kb_ids=accessible_kbs, top_k=req.top_k
                )
                fused = rrf_fuse(keyword_hits=kw_hits, vector_hits=vec_hits)
                total = len(fused)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "hybrid_search_fallback_to_keyword",
                    error_type=type(exc).__name__,
                )
                actual_mode = "keyword"
                fused = kw_hits

    # 重排在答案生成前完成；未显式指定时使用首个已启用且已配置密钥的模型。
    informative = [hit for hit in fused if _has_retrieval_information(hit)]
    if informative:
        fused = informative
    forced_rerank = req.top_k > settings.rag_max_top_k
    do_rerank = req.rerank or forced_rerank
    reranked = False
    if do_rerank:
        ts = time.time()
        rerank_model_id = await _resolve_rerank_model_id(db, req.rerank_model_id)
        fused, reranked = await _rerank(
            db,
            query=req.query,
            candidates=fused,
            rerank_model_id=rerank_model_id,
            top_k=req.top_k,
        )
        debug_rt = int((time.time() - ts) * 1000)
    else:
        fused = fused[: req.top_k]

    # 阈值作用于最终相关性分数，避免用约 0.016 的 RRF 分数误删全部结果。
    if req.threshold > 0:
        fused = [hit for hit in fused if _score_from_hit(hit) >= req.threshold]

    # 结果后置权限过滤
    safe = post_filter_hits(hits=fused, accessible_kb_ids=accessible_kbs)
    hits = [_row_to_hit(hit) for hit in safe]

    took_ms = int((time.time() - start) * 1000)
    return SearchResponse(
        hits=hits,
        mode=actual_mode,
        reranked=reranked,
        took_ms=took_ms,
        total_candidates=total,
        debug=SearchDebug(
            embedding_latency_ms=debug_vt or None,
            keyword_latency_ms=debug_kt or None,
            rerank_latency_ms=debug_rt or None,
        ),
    )


def _build_answer_messages(query: str, hits: list[SearchHit]) -> list[dict[str, str]]:
    context_chunks: list[str] = []
    used_chars = 0
    for index, hit in enumerate(hits, start=1):
        text_value = hit.text.strip()
        if not text_value:
            continue
        header = f"[{index}] 文档：{hit.doc_title or hit.doc_id}；片段：{hit.chunk_id}"
        chunk = f"{header}\n{text_value}"
        next_size = used_chars + len(chunk)
        if next_size > settings.rag_answer_max_context_chars:
            remaining = settings.rag_answer_max_context_chars - used_chars
            if remaining <= 200:
                break
            chunk = chunk[:remaining]
        context_chunks.append(chunk)
        used_chars += len(chunk)

    context = "\n\n---\n\n".join(context_chunks) if context_chunks else "未检索到可用片段。"
    system = (
        "你是企业知识库 RAG 问答助手。必须只依据给定资料回答，不得编造。"
        "请先综合资料形成直接回答，再给出关键依据。"
        "引用依据时使用 [1]、[2] 这样的编号。"
        "如果资料不足以回答，明确说明“未在文档中找到相关引用”，并指出还需要什么信息。"
        "不要逐字复述全部原文。"
    )
    user_content = f"用户问题：{query}\n\n检索资料：\n{context}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]


async def _resolve_chat_model(
    db: AsyncSession,
    *,
    chat_model_id: str | None,
) -> tuple[str, str, str, str]:
    if chat_model_id:
        model = await model_service.get_model(db, chat_model_id)
        if model is None or model.kind != "chat" or not model.enabled:
            raise ValidationException(message="chat_model_id 不存在或不是聊天模型")
        provider = await model_service.get_provider(db, model.provider_code)
        if provider is None or not provider.enabled:
            raise ValidationException(message="模型 Provider 不存在")
        api_key = decrypt_api_key(model.api_key_encrypted) if model.api_key_encrypted else ""
        return provider.code, provider.base_url, model.model_name, api_key

    api_key = settings.deepseek_api_key.strip() or settings.model_api_key.strip()
    if not api_key:
        raise ValidationException(
            message="未选择可用聊天模型，且环境变量兜底模型未配置 API Key"
        )
    return (
        "deepseek",
        settings.deepseek_base_url,
        settings.deepseek_chat_model,
        api_key,
    )


async def answer(
    db: AsyncSession,
    *,
    user: User,
    req: RagAnswerRequest,
) -> RagAnswerResponse:
    start = time.time()
    await ensure_safe_query(req.query)
    cached = await get_cached_answer(
        user_id=user.id,
        kb_id=req.kb_id,
        query=req.query,
    )
    if cached is not None:
        cached.took_ms = int((time.time() - start) * 1000)
        logger.info("rag_answer_cache_hit", kb_id=req.kb_id)
        return cached

    search_resp = await search(db, user=user, req=req, guard_checked=True)

    if not search_resp.hits:
        return RagAnswerResponse(
            answer="未在文档中找到相关引用。请确认文档已处理完成，或换一个更贴近文档标题、章节、关键词的问题。",
            hits=[],
            mode=search_resp.mode,
            took_ms=search_resp.took_ms,
            model=None,
            conversation_id=None,
            generated=False,
            from_cache=False,
        )

    provider_code, base_url, model_name, api_key = await _resolve_chat_model(
        db, chat_model_id=req.chat_model_id
    )
    provider: OpenAICompatibleProvider = build_provider(
        provider_code,
        base_url,
        api_key,
        timeout=settings.model_provider_timeout_seconds,
    )
    try:
        generated = await provider.chat(
            model_name=model_name,
            messages=_build_answer_messages(req.query, search_resp.hits),
            temperature=0.2,
            max_tokens=settings.rag_answer_max_tokens,
            stream=False,
            timeout=settings.model_provider_timeout_seconds,
        )
    except Exception as exc:  # noqa: BLE001
        status = getattr(getattr(exc, "response", None), "status_code", None)
        logger.warning(
            "rag_chat_provider_failed",
            error_type=type(exc).__name__,
            status_code=status,
            model=model_name,
        )
        # 检索已成功时仍返回引用，便于排查模型 Key；不写入问答缓存
        return RagAnswerResponse(
            answer=(
                f"已检索到 {len(search_resp.hits)} 条相关片段，但聊天模型调用失败"
                f"（{status or type(exc).__name__}）。"
                "请检查所选供应商的 API Key、Base URL 与模型名。"
            ),
            hits=search_resp.hits,
            mode=search_resp.mode,
            took_ms=int((time.time() - start) * 1000),
            model=model_name,
            conversation_id=None,
            generated=False,
            from_cache=False,
        )
    answer_text = strip_model_think_blocks(
        generated if isinstance(generated, str) else ""
    )
    response = RagAnswerResponse(
        answer=answer_text.strip() or "未在文档中找到相关引用。",
        hits=search_resp.hits,
        mode=search_resp.mode,
        took_ms=int((time.time() - start) * 1000),
        model=model_name,
        conversation_id=None,
        generated=True,
        from_cache=False,
    )
    await set_cached_answer(
        user_id=user.id,
        kb_id=req.kb_id,
        query=req.query,
        response=response,
    )
    return response
