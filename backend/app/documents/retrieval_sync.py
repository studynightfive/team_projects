"""将 document_chunks 同步到检索用 chunks 表，并按需同步 Milvus。

设计：
- document_chunks 仍是员工 4 的权威分段与世代管理（index_generation / is_active）
- chunks 是员工 5 检索/问答的只读索引投影；仅投影当前 is_active=true 的分段
- VECTOR_BACKEND=milvus|dual 时额外写入 Milvus（HNSW）
"""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.documents.indexing import DocumentIndexingService
from app.documents.models import Document, DocumentChunk
from app.rag.embeddings import LOCAL_EMBEDDING_MODEL_ID
from app.rag.search.repository import Chunk
from app.rag.vector_store import VectorRecord, get_vector_backend_name, get_vector_store

__all__ = [
    "LOCAL_EMBEDDING_MODEL_ID",
    "build_retrieval_metadata",
    "publish_document_to_retrieval",
    "to_retrieval_chunk",
    "unpublish_document_from_retrieval",
]


def build_retrieval_metadata(
    chunk: DocumentChunk,
    *,
    doc_title: str | None,
) -> dict:
    return {
        "heading": chunk.heading,
        "chunk_no": chunk.chunk_no,
        "section_no": chunk.section_no,
        "char_start": chunk.char_start,
        "char_end": chunk.char_end,
        "token_estimate": chunk.token_estimate,
        "index_generation": chunk.index_generation,
        "doc_title": doc_title,
    }


def to_retrieval_chunk(
    chunk: DocumentChunk,
    *,
    doc_title: str | None,
    indexer: DocumentIndexingService | None = None,
) -> Chunk:
    """把一条活跃 DocumentChunk 映射为检索 Chunk（纯函数，便于单测）。"""
    service = indexer or DocumentIndexingService()
    return Chunk(
        chunk_id=chunk.id,
        doc_id=chunk.document_id,
        kb_id=chunk.knowledge_base_id,
        content=chunk.content,
        page=chunk.page_no,
        embedding=service.deserialize_embedding(chunk.embedding_json),
        metadata_=build_retrieval_metadata(chunk, doc_title=doc_title),
    )


async def publish_document_to_retrieval(session: AsyncSession, document_id: str) -> int:
    """用当前活跃 document_chunks 整文档替换检索投影。返回写入条数。"""
    await session.execute(delete(Chunk).where(Chunk.doc_id == document_id))

    doc = await session.get(Document, document_id)
    doc_title = doc.title if doc is not None else None

    result = await session.execute(
        select(DocumentChunk).where(
            DocumentChunk.document_id == document_id,
            DocumentChunk.is_active.is_(True),
        )
    )
    active = list(result.scalars())
    indexer = DocumentIndexingService()
    orm_rows: list[Chunk] = []
    for row in active:
        mapped = to_retrieval_chunk(row, doc_title=doc_title, indexer=indexer)
        session.add(mapped)
        orm_rows.append(mapped)
    await session.flush()

    backend = get_vector_backend_name()
    if backend in {"milvus", "dual"} and orm_rows:
        store = await get_vector_store(session)
        records = [
            VectorRecord(
                chunk_id=c.chunk_id,
                doc_id=c.doc_id,
                kb_id=c.kb_id,
                content=c.content,
                page=c.page,
                embedding=list(c.embedding or []),
                metadata=dict(c.metadata_ or {}),
            )
            for c in orm_rows
        ]
        await store.delete_by_doc(document_id)
        await store.upsert(records)
    return len(active)


async def unpublish_document_from_retrieval(session: AsyncSession, document_id: str) -> None:
    """从检索索引移除该文档全部投影（停用索引或删除文档时调用）。"""
    await session.execute(delete(Chunk).where(Chunk.doc_id == document_id))
    await session.flush()
    backend = get_vector_backend_name()
    if backend in {"milvus", "dual"}:
        store = await get_vector_store(session)
        await store.delete_by_doc(document_id)
