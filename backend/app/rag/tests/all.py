"""命中率测试（提示词 06）—— schemas + repository + service + metrics + api 单文件版

指标：hit_rate / MRR / NDCG@K / Recall@K / Precision@K / MAP@K
可复现：固化 config_hash；每次运行都重新执行真实检索。
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from typing import Literal, TypedDict, cast
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.auth.dependencies import get_current_user, require_permission
from app.common.config import settings
from app.common.database import Base, get_db
from app.common.exceptions import NotFoundException, ValidationException
from app.common.models import User
from app.common.schemas import APIResponse, PaginatedData
from app.documents.models import DocumentChunk
from app.rag._shared.audit_helper import audit
from app.rag.search import service as search_service
from app.rag.search.schemas import SearchRequest

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/retrieval-tests", tags=["retrieval-tests"])

SearchMode = Literal["keyword", "vector", "hybrid"]


class StoredRetrievalTestQuery(TypedDict):
    query: str
    relevant_chunk_ids: list[str]
    notes: str | None


# ============================================================
# ORM 模型
# ============================================================
class RetrievalTestDataset(Base):
    __tablename__ = "retrieval_test_datasets"
    __table_args__ = (Index("ix_test_dataset_kb", "kb_id"),)

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False).with_variant(String(36), "sqlite"),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    kb_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False).with_variant(String(36), "sqlite"),
        nullable=False,
    )
    queries: Mapped[list[StoredRetrievalTestQuery]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    created_by: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RetrievalTestRun(Base):
    __tablename__ = "retrieval_test_runs"
    __table_args__ = (
        Index("ix_test_run_dataset", "dataset_id"),
        Index("ix_test_run_hash", "dataset_id", "config_hash"),
        Index("ix_test_run_status", "status"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False).with_variant(String(36), "sqlite"),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    dataset_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False).with_variant(String(36), "sqlite"),
        ForeignKey("retrieval_test_datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    config: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    config_hash: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    metrics: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    per_query: Mapped[list[dict[str, object]] | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ============================================================
# Schemas
# ============================================================
class RetrievalTestQuery(BaseModel):
    query: str = Field(min_length=1)
    relevant_chunk_ids: list[str] = Field(min_length=1)
    notes: str | None = None


class RetrievalTestDatasetCreate(BaseModel):
    name: str = Field(max_length=200)
    description: str = ""
    kb_id: str
    queries: list[RetrievalTestQuery]


class RetrievalTestDatasetUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = None
    queries: list[RetrievalTestQuery] | None = None


class RetrievalTestDatasetResponse(BaseModel):
    id: str
    name: str
    description: str
    kb_id: str
    queries: list[RetrievalTestQuery]
    created_by: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}


class RetrievalTestConfig(BaseModel):
    mode: SearchMode
    top_k: int = Field(ge=1, le=50)
    rerank: bool = True
    threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    embedding_model_id: str | None = None
    rerank_model_id: str | None = None
    metadata_filter: dict[str, object] | None = None


class RetrievalTestRequest(BaseModel):
    dataset_id: str
    config: RetrievalTestConfig
    async_run: bool = False


class SingleRetrievalTestRequest(BaseModel):
    kb_id: str
    question: str = Field(min_length=1, max_length=2000)
    config: RetrievalTestConfig


class SingleRetrievalTestResponse(BaseModel):
    question: str
    hit: bool
    hit_rate: float
    threshold: float
    hits: list[dict[str, object]]
    took_ms: int


class RetrievalTestMetrics(BaseModel):
    hit_rate: float
    mrr: float
    ndcg_at_k: float
    recall_at_k: float
    precision_at_k: float
    map_at_k: float


class PerQueryResult(BaseModel):
    query: str
    relevant_chunk_ids: list[str]
    retrieved_chunk_ids: list[str]
    hit: bool
    reciprocal_rank: float
    ndcg: float
    recall: float
    precision: float
    average_precision: float = 0.0
    latency_ms: int


class RetrievalTestResult(BaseModel):
    id: str
    dataset_id: str
    config: RetrievalTestConfig
    config_hash: str
    total: int
    metrics: RetrievalTestMetrics
    per_query: list[PerQueryResult]
    started_at: datetime | None = None
    finished_at: datetime | None = None


class RetrievalTestRunSummary(BaseModel):
    id: str
    status: Literal["pending", "running", "done", "failed"]
    progress: int
    result: RetrievalTestResult | None = None
    error_message: str | None = None


# ============================================================
# 6 个指标（对齐 ragas）
# ============================================================
def _hit(retrieved: list[str], relevant: set[str]) -> bool:
    return any(r in relevant for r in retrieved)


def _reciprocal_rank(retrieved: list[str], relevant: set[str]) -> float:
    for i, r in enumerate(retrieved, start=1):
        if r in relevant:
            return 1.0 / i
    return 0.0


def _ndg_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    dcg = sum((1.0 / math.log2(i + 2)) for i, r in enumerate(retrieved[:k]) if r in relevant)
    ideal = sum(1.0 / math.log2(i + 2) for i in range(min(k, len(relevant))))
    return dcg / ideal if ideal > 0 else 0.0


def _recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    return len([r for r in retrieved[:k] if r in relevant]) / len(relevant)


def _precision_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if k == 0:
        return 0.0
    return len([r for r in retrieved[:k] if r in relevant]) / k


def _average_precision_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    hits = 0
    s = 0.0
    for i, r in enumerate(retrieved[:k], start=1):
        if r in relevant:
            hits += 1
            s += hits / i
    return s / len(relevant)


def _aggregate_metrics(per_query: list[PerQueryResult]) -> RetrievalTestMetrics:
    n = len(per_query) or 1
    return RetrievalTestMetrics(
        hit_rate=sum(p.hit for p in per_query) / n,
        mrr=sum(p.reciprocal_rank for p in per_query) / n,
        ndcg_at_k=sum(p.ndcg for p in per_query) / n,
        recall_at_k=sum(p.recall for p in per_query) / n,
        precision_at_k=sum(p.precision for p in per_query) / n,
        map_at_k=sum(p.average_precision for p in per_query) / n,
    )


# ============================================================
# config 哈希（用于可复现性）
# ============================================================
def _hash_config(cfg: RetrievalTestConfig) -> str:
    raw = json.dumps(cfg.model_dump(), sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def _store_query(query: RetrievalTestQuery) -> StoredRetrievalTestQuery:
    return {
        "query": query.query,
        "relevant_chunk_ids": query.relevant_chunk_ids,
        "notes": query.notes,
    }


async def _resolve_relevant_chunk_ids(
    db: AsyncSession, chunk_ids: list[str]
) -> list[str]:
    """把重处理前的标签精确映射到同一文档、相同内容的新活动分块。"""
    rows = list(
        (
            await db.execute(
                select(DocumentChunk).where(DocumentChunk.id.in_(chunk_ids))
            )
        ).scalars()
    )
    by_id = {str(row.id): row for row in rows}
    resolved: list[str] = []
    for chunk_id in chunk_ids:
        old = by_id.get(chunk_id)
        if old is None:
            raise ValidationException(
                message=f"测试标签分块 {chunk_id} 已不存在，请重新标注测试集"
            )
        if old.is_active:
            resolved.append(str(old.id))
            continue
        replacement = (
            await db.execute(
                select(DocumentChunk.id).where(
                    DocumentChunk.document_id == old.document_id,
                    DocumentChunk.content == old.content,
                    DocumentChunk.is_active.is_(True),
                )
            )
        ).scalars().first()
        if replacement is None:
            raise ValidationException(
                message="测试集标签已因文档重切分失效，请重新选择相关分块后再运行"
            )
        resolved.append(str(replacement))
    return list(dict.fromkeys(resolved))


# ============================================================
# 数据集 CRUD
# ============================================================
async def list_datasets(
    db: AsyncSession, *, user_id: str, page: int, page_size: int
) -> tuple[list[RetrievalTestDataset], int]:
    q = select(RetrievalTestDataset)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
    offset = (page - 1) * page_size
    res = await db.execute(
        q.order_by(RetrievalTestDataset.created_at.desc()).offset(offset).limit(page_size)
    )
    return list(res.scalars().all()), total


async def create_dataset(
    db: AsyncSession, *, user_id: str, payload: RetrievalTestDatasetCreate
) -> RetrievalTestDataset:
    if len(payload.queries) > settings.retrieval_test_max_queries:
        raise ValidationException(message=f"queries 上限 {settings.retrieval_test_max_queries}")
    ds = RetrievalTestDataset(
        name=payload.name,
        description=payload.description,
        kb_id=payload.kb_id,
        queries=[_store_query(query) for query in payload.queries],
        created_by=user_id,
    )
    db.add(ds)
    return ds


async def get_dataset(db: AsyncSession, dataset_id: str) -> RetrievalTestDataset | None:
    return await db.get(RetrievalTestDataset, dataset_id)


async def update_dataset(
    db: AsyncSession, ds: RetrievalTestDataset, payload: RetrievalTestDatasetUpdate
) -> RetrievalTestDataset:
    if payload.name is not None:
        ds.name = payload.name
    if payload.description is not None:
        ds.description = payload.description
    if payload.queries is not None:
        if len(payload.queries) > settings.retrieval_test_max_queries:
            raise ValidationException(message=f"queries 上限 {settings.retrieval_test_max_queries}")
        ds.queries = [_store_query(query) for query in payload.queries]
    return ds


async def delete_dataset(db: AsyncSession, ds: RetrievalTestDataset) -> None:
    await db.delete(ds)


# ============================================================
# 运行测试
# ============================================================
async def _run_evaluation(
    db: AsyncSession,
    *,
    user: User,
    dataset: RetrievalTestDataset,
    config: RetrievalTestConfig,
) -> RetrievalTestRun:
    run = RetrievalTestRun(
        dataset_id=dataset.id,
        config=config.model_dump(),
        config_hash=_hash_config(config),
        status="running",
        progress=0,
        total=len(dataset.queries),
    )
    db.add(run)
    await db.commit()

    # 每次运行都真实检索，config_hash 仅用于对比相同参数的历史结果。
    per_query_results: list[PerQueryResult] = []
    n = len(dataset.queries)
    normalized_queries: list[StoredRetrievalTestQuery] = []
    for i, q in enumerate(dataset.queries, start=1):
        resolved_ids = await _resolve_relevant_chunk_ids(db, q["relevant_chunk_ids"])
        relevant = set(resolved_ids)
        normalized_queries.append(
            {
                "query": q["query"],
                "relevant_chunk_ids": resolved_ids,
                "notes": q.get("notes"),
            }
        )
        qtext = q["query"]
        start = datetime.now(timezone.utc)
        try:
            resp = await search_service.search(
                db,
                user=user,
                req=SearchRequest(
                    query=qtext,
                    mode=config.mode,
                    kb_id=dataset.kb_id,
                    top_k=config.top_k,
                    threshold=config.threshold,
                    metadata_filter=config.metadata_filter,
                    rerank=config.rerank,
                    rerank_model_id=config.rerank_model_id,
                    embedding_model_id=config.embedding_model_id,
                ),
            )
            retrieved = [h.chunk_id for h in resp.hits]
        except Exception as exc:
            logger.warning("test_query_failed", error_type=type(exc).__name__)
            run.status = "failed"
            run.error_message = f"第 {i} 个问题检索失败：{type(exc).__name__}"
            run.finished_at = datetime.now(timezone.utc)
            await db.commit()
            raise ValidationException(
                message=f"第 {i} 个问题检索失败，请检查模型和知识库索引配置"
            ) from exc
        latency = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
        k = config.top_k
        per_query_results.append(
            PerQueryResult(
                query=qtext,
                relevant_chunk_ids=list(relevant),
                retrieved_chunk_ids=retrieved,
                hit=_hit(retrieved, relevant),
                reciprocal_rank=_reciprocal_rank(retrieved, relevant),
                ndcg=_ndg_at_k(retrieved, relevant, k),
                recall=_recall_at_k(retrieved, relevant, k),
                precision=_precision_at_k(retrieved, relevant, k),
                average_precision=_average_precision_at_k(retrieved, relevant, k),
                latency_ms=latency,
            )
        )
        run.progress = int(i / n * 100)
        await db.commit()

    if normalized_queries != dataset.queries:
        dataset.queries = normalized_queries
    run.metrics = _aggregate_metrics(per_query_results).model_dump()
    run.per_query = [p.model_dump() for p in per_query_results]
    run.status = "done"
    run.finished_at = datetime.now(timezone.utc)
    await db.commit()
    return run


# ============================================================
# 路由
# ============================================================
@router.get("/datasets")
async def list_datasets_endpoint(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.retrieval_test.run")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    items, total = await list_datasets(db, user_id=user.id, page=page, page_size=page_size)
    return APIResponse(
        data=PaginatedData(
            items=[RetrievalTestDatasetResponse.model_validate(d).model_dump() for d in items],
            page=page,
            page_size=page_size,
            total=total,
        ).model_dump()
    ).model_dump()


@router.post("/datasets", status_code=status.HTTP_201_CREATED)
async def create_dataset_endpoint(
    request: Request,
    payload: RetrievalTestDatasetCreate,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.retrieval_test.run")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    ds = await create_dataset(db, user_id=user.id, payload=payload)
    await db.commit()
    await db.refresh(ds)
    await audit(
        db,
        action="retrieval_test_dataset_create",
        user_id=user.id,
        resource_type="retrieval_test_dataset",
        resource_id=ds.id,
        request=request,
    )
    await db.commit()
    return APIResponse(
        data=RetrievalTestDatasetResponse.model_validate(ds).model_dump()
    ).model_dump()


@router.get("/datasets/{dataset_id}")
async def get_dataset_endpoint(
    dataset_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.retrieval_test.run")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    ds = await get_dataset(db, dataset_id)
    if ds is None:
        raise NotFoundException()
    return APIResponse(
        data=RetrievalTestDatasetResponse.model_validate(ds).model_dump()
    ).model_dump()


@router.patch("/datasets/{dataset_id}")
async def patch_dataset_endpoint(
    dataset_id: str,
    request: Request,
    payload: RetrievalTestDatasetUpdate,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.retrieval_test.run")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    ds = await get_dataset(db, dataset_id)
    if ds is None:
        raise NotFoundException()
    ds = await update_dataset(db, ds, payload)
    await db.commit()
    await db.refresh(ds)
    return APIResponse(
        data=RetrievalTestDatasetResponse.model_validate(ds).model_dump()
    ).model_dump()


@router.delete("/datasets/{dataset_id}")
async def delete_dataset_endpoint(
    dataset_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.retrieval_test.run")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    ds = await get_dataset(db, dataset_id)
    if ds is None:
        raise NotFoundException()
    await delete_dataset(db, ds)
    await db.commit()
    await audit(
        db,
        action="retrieval_test_dataset_delete",
        user_id=user.id,
        resource_id=dataset_id,
        request=request,
    )
    await db.commit()
    return APIResponse().model_dump()


@router.post("/run")
async def run_test_endpoint(
    request: Request,
    payload: RetrievalTestRequest,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.retrieval_test.run")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    dataset = await get_dataset(db, payload.dataset_id)
    if dataset is None:
        raise NotFoundException()

    if payload.async_run:
        raise ValidationException(message="异步评测尚未接入 Worker，请使用 async_run=false")

    run = await _run_evaluation(db, user=user, dataset=dataset, config=payload.config)
    return APIResponse(
        data=RetrievalTestResult(
            id=run.id,
            dataset_id=run.dataset_id,
            config=RetrievalTestConfig.model_validate(run.config),
            config_hash=run.config_hash,
            total=run.total,
            metrics=RetrievalTestMetrics.model_validate(run.metrics),
            per_query=[PerQueryResult.model_validate(p) for p in (run.per_query or [])],
            started_at=run.started_at,
            finished_at=run.finished_at,
        ).model_dump()
    ).model_dump()


@router.post("/single")
async def run_single_test_endpoint(
    request: Request,
    payload: SingleRetrievalTestRequest,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.retrieval_test.run")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    response = await search_service.search(
        db,
        user=user,
        req=SearchRequest(
            query=payload.question,
            mode=payload.config.mode,
            kb_id=payload.kb_id,
            top_k=payload.config.top_k,
            threshold=payload.config.threshold,
            metadata_filter=payload.config.metadata_filter,
            rerank=payload.config.rerank,
            rerank_model_id=payload.config.rerank_model_id,
            embedding_model_id=payload.config.embedding_model_id,
        ),
    )
    hit = len(response.hits) > 0
    await audit(
        db,
        action="retrieval_test_single",
        user_id=user.id,
        resource_type="kb",
        resource_id=payload.kb_id,
        detail=(
            f"mode={payload.config.mode} top_k={payload.config.top_k} "
            f"threshold={payload.config.threshold} hit={hit}"
        ),
        request=request,
    )
    await db.commit()
    return APIResponse(
        data=SingleRetrievalTestResponse(
            question=payload.question,
            hit=hit,
            hit_rate=1.0 if hit else 0.0,
            threshold=payload.config.threshold,
            hits=[item.model_dump() for item in response.hits],
            took_ms=response.took_ms,
        ).model_dump()
    ).model_dump()


@router.get("/runs")
async def list_runs_endpoint(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.retrieval_test.run")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    q = select(RetrievalTestRun)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
    offset = (page - 1) * page_size
    res = await db.execute(
        q.order_by(RetrievalTestRun.started_at.desc()).offset(offset).limit(page_size)
    )
    items: list[dict[str, object]] = []
    for r in res.scalars().all():
        items.append(
            {
                "id": r.id,
                "dataset_id": r.dataset_id,
                "config_hash": r.config_hash,
                "status": r.status,
                "progress": r.progress,
                "total": r.total,
                "started_at": r.started_at,
                "finished_at": r.finished_at,
            }
        )
    return APIResponse(
        data=PaginatedData(items=items, page=page, page_size=page_size, total=total).model_dump()
    ).model_dump()


@router.get("/runs/{run_id}")
async def get_run_endpoint(
    run_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.retrieval_test.run")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    run = await db.get(RetrievalTestRun, run_id)
    if run is None:
        raise NotFoundException()
    if not run.metrics or not run.per_query:
        return APIResponse(
            data=RetrievalTestRunSummary(
                id=run.id,
                status=cast(Literal["pending", "running", "done", "failed"], run.status),
                progress=run.progress,
                error_message=run.error_message,
            ).model_dump()
        ).model_dump()
    return APIResponse(
        data=RetrievalTestResult(
            id=run.id,
            dataset_id=run.dataset_id,
            config=RetrievalTestConfig.model_validate(run.config),
            config_hash=run.config_hash,
            total=run.total,
            metrics=RetrievalTestMetrics.model_validate(run.metrics),
            per_query=[PerQueryResult.model_validate(p) for p in run.per_query],
            started_at=run.started_at,
            finished_at=run.finished_at,
        ).model_dump()
    ).model_dump()
