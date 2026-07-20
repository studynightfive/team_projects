"""向量后端抽象：pgvector（默认）与可选 Milvus。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class VectorHit:
    chunk_id: str
    doc_id: str
    kb_id: str
    page: int | None
    content: str
    metadata: dict
    score: float


@dataclass
class VectorRecord:
    chunk_id: str
    doc_id: str
    kb_id: str
    content: str
    page: int | None
    embedding: list[float]
    metadata: dict


class VectorStore(Protocol):
    async def upsert(self, records: list[VectorRecord]) -> None: ...

    async def delete_by_doc(self, doc_id: str) -> None: ...

    async def search(
        self,
        *,
        embedding: list[float],
        accessible_kb_ids: set[str],
        top_k: int,
    ) -> list[VectorHit]: ...


def get_vector_backend_name() -> str:
    from app.common.config import settings

    return (settings.vector_backend or "pgvector").lower()


async def get_vector_store(db: AsyncSession) -> VectorStore:
    name = get_vector_backend_name()
    if name == "milvus":
        from app.rag.vector_store.milvus import MilvusVectorStore

        return MilvusVectorStore()
    if name == "dual":
        from app.rag.vector_store.dual import DualVectorStore
        from app.rag.vector_store.milvus import MilvusVectorStore
        from app.rag.vector_store.pgvector import PgVectorStore

        return DualVectorStore(primary=PgVectorStore(db), secondary=MilvusVectorStore())
    from app.rag.vector_store.pgvector import PgVectorStore

    return PgVectorStore(db)
