"""PostgreSQL + pgvector 向量检索后端。"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.embeddings import embedding_literal
from app.rag.vector_store import VectorHit, VectorRecord


class PgVectorStore:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upsert(self, records: list[VectorRecord]) -> None:
        # 权威写入仍由 retrieval_sync 写 chunks 表；此处 no-op，避免双写冲突
        return None

    async def delete_by_doc(self, doc_id: str) -> None:
        return None

    async def search(
        self,
        *,
        embedding: list[float],
        accessible_kb_ids: set[str],
        top_k: int,
    ) -> list[VectorHit]:
        if not accessible_kb_ids:
            return []
        kb_list = list(accessible_kb_ids)
        emb = embedding_literal(embedding)
        sql = text(
            """
            SELECT chunk_id, doc_id, kb_id, page, content, metadata,
                   1 - (embedding::vector <=> CAST(:emb AS vector)) AS score
            FROM chunks
            WHERE kb_id = ANY(:kb_ids)
              AND embedding IS NOT NULL
            ORDER BY embedding::vector <=> CAST(:emb AS vector)
            LIMIT :limit
            """
        )
        res = await self.db.execute(sql, {"emb": emb, "kb_ids": kb_list, "limit": top_k * 2})
        hits: list[VectorHit] = []
        for r in res.fetchall():
            row = dict(r._mapping)
            meta = row.get("metadata") or {}
            if not isinstance(meta, dict):
                meta = {}
            hits.append(
                VectorHit(
                    chunk_id=row["chunk_id"],
                    doc_id=row["doc_id"],
                    kb_id=row["kb_id"],
                    page=row.get("page"),
                    content=row.get("content") or "",
                    metadata=meta,
                    score=float(row.get("score") or 0.0),
                )
            )
        return hits
