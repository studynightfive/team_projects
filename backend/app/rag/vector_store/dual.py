"""双写：pgvector 权威检索 + Milvus 旁路索引（VECTOR_BACKEND=dual）。"""

from __future__ import annotations

import structlog

from app.rag.vector_store import VectorHit, VectorRecord, VectorStore

logger = structlog.get_logger()


class DualVectorStore:
    def __init__(self, *, primary: VectorStore, secondary: VectorStore) -> None:
        self.primary = primary
        self.secondary = secondary

    async def upsert(self, records: list[VectorRecord]) -> None:
        await self.primary.upsert(records)
        try:
            await self.secondary.upsert(records)
        except Exception as exc:
            logger.warning("dual_milvus_upsert_failed", error=str(exc)[:200])

    async def delete_by_doc(self, doc_id: str) -> None:
        await self.primary.delete_by_doc(doc_id)
        try:
            await self.secondary.delete_by_doc(doc_id)
        except Exception as exc:
            logger.warning("dual_milvus_delete_failed", error=str(exc)[:200])

    async def search(
        self,
        *,
        embedding: list[float],
        accessible_kb_ids: set[str],
        top_k: int,
    ) -> list[VectorHit]:
        # dual 模式下检索仍以 primary(pgvector) 为准，保证权限与一致性
        return await self.primary.search(
            embedding=embedding,
            accessible_kb_ids=accessible_kb_ids,
            top_k=top_k,
        )
