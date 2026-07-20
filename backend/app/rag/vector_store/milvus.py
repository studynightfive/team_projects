"""Milvus 向量后端（可选）。

未安装 pymilvus 或未连通时：
- upsert/delete 记录 warning 并跳过（不阻断入库）
- search 抛出明确错误，提示检查 VECTOR_BACKEND / MILVUS_URI

集合字段：chunk_id, doc_id, kb_id, page, content, embedding, metadata_json
索引：HNSW + COSINE（与图解文档一致）
"""

from __future__ import annotations

import json
import threading
from typing import Any

import structlog

from app.common.config import settings
from app.rag.vector_store import VectorHit, VectorRecord

logger = structlog.get_logger()

_lock = threading.Lock()
_collection_ready = False


def _import_milvus() -> Any:
    try:
        from pymilvus import (  # type: ignore[import-not-found]
            Collection,
            CollectionSchema,
            DataType,
            FieldSchema,
            connections,
            utility,
        )
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "未安装 pymilvus。请安装后重试，或将 VECTOR_BACKEND 设为 pgvector。"
        ) from exc
    return connections, utility, Collection, CollectionSchema, FieldSchema, DataType


class MilvusVectorStore:
    def __init__(self) -> None:
        self.collection_name = settings.milvus_collection
        self.dim = settings.milvus_embedding_dim

    def _connect(self) -> Any:
        connections, utility, Collection, CollectionSchema, FieldSchema, DataType = _import_milvus()  # noqa: N806
        uri = settings.milvus_uri
        token = settings.milvus_token or None
        connections.connect(alias="default", uri=uri, token=token)
        return connections, utility, Collection, CollectionSchema, FieldSchema, DataType

    def _ensure_collection(self) -> Any:
        global _collection_ready
        connections, utility, Collection, CollectionSchema, FieldSchema, DataType = self._connect()  # noqa: N806
        with _lock:
            if utility.has_collection(self.collection_name):
                col = Collection(self.collection_name)
                col.load()
                _collection_ready = True
                return col
            fields = [
                FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),  # noqa: E501
                FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=36),
                FieldSchema(name="kb_id", dtype=DataType.VARCHAR, max_length=36),
                FieldSchema(name="page", dtype=DataType.INT64),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="metadata_json", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dim),
            ]
            schema = CollectionSchema(fields, description="kb chunks")
            col = Collection(self.collection_name, schema)
            col.create_index(
                "embedding",
                {
                    "index_type": "HNSW",
                    "metric_type": "COSINE",
                    "params": {"M": settings.milvus_hnsw_m, "efConstruction": settings.milvus_hnsw_ef_construction},  # noqa: E501
                },
            )
            col.load()
            _collection_ready = True
            return col

    async def upsert(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        try:
            col = self._ensure_collection()
            # 先删同 chunk，再插入（幂等）
            ids = [r.chunk_id for r in records]
            expr = "chunk_id in [" + ",".join(f'"{i}"' for i in ids) + "]"
            try:
                col.delete(expr)
            except Exception:
                pass
            entities = [
                [r.chunk_id for r in records],
                [r.doc_id for r in records],
                [r.kb_id for r in records],
                [int(r.page or 0) for r in records],
                [r.content[:65000] for r in records],
                [json.dumps(r.metadata, ensure_ascii=False)[:65000] for r in records],
                [self._pad(r.embedding) for r in records],
            ]
            col.insert(entities)
            col.flush()
        except Exception as exc:
            logger.warning("milvus_upsert_skipped", error=str(exc)[:200])

    async def delete_by_doc(self, doc_id: str) -> None:
        try:
            col = self._ensure_collection()
            col.delete(f'doc_id == "{doc_id}"')
            col.flush()
        except Exception as exc:
            logger.warning("milvus_delete_skipped", error=str(exc)[:200])

    async def search(
        self,
        *,
        embedding: list[float],
        accessible_kb_ids: set[str],
        top_k: int,
    ) -> list[VectorHit]:
        if not accessible_kb_ids:
            return []
        col = self._ensure_collection()
        kb_list = list(accessible_kb_ids)
        expr = "kb_id in [" + ",".join(f'"{k}"' for k in kb_list) + "]"
        results = col.search(
            data=[self._pad(embedding)],
            anns_field="embedding",
            param={"metric_type": "COSINE", "params": {"ef": settings.milvus_hnsw_ef_search}},
            limit=top_k * 2,
            expr=expr,
            output_fields=["chunk_id", "doc_id", "kb_id", "page", "content", "metadata_json"],
        )
        hits: list[VectorHit] = []
        for hits_group in results:
            for h in hits_group:
                entity = h.entity
                meta_raw = entity.get("metadata_json") or "{}"
                try:
                    meta = json.loads(meta_raw)
                except Exception:
                    meta = {}
                page = entity.get("page")
                hits.append(
                    VectorHit(
                        chunk_id=entity.get("chunk_id") or h.id,
                        doc_id=entity.get("doc_id") or "",
                        kb_id=entity.get("kb_id") or "",
                        page=None if page in (None, 0) else int(page),
                        content=entity.get("content") or "",
                        metadata=meta if isinstance(meta, dict) else {},
                        score=float(h.score),
                    )
                )
        return hits

    def _pad(self, embedding: list[float]) -> list[float]:
        if len(embedding) == self.dim:
            return embedding
        if len(embedding) > self.dim:
            return embedding[: self.dim]
        return embedding + [0.0] * (self.dim - len(embedding))
