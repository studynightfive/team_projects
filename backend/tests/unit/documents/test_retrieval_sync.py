"""入库 → 检索投影同步单元测试。"""

from __future__ import annotations

import json
import uuid

from app.documents.indexing import DocumentIndexingService, deterministic_embedding
from app.documents.models import DocumentChunk
from app.documents.retrieval_sync import (
    LOCAL_EMBEDDING_MODEL_ID,
    build_retrieval_metadata,
    to_retrieval_chunk,
)
from app.rag.embeddings import is_local_embedding
from app.rag.search.service import _embedding_literal, _row_to_hit


def _make_chunk(**overrides: object) -> DocumentChunk:
    embedding = deterministic_embedding("知识库段落", 8)
    base = {
        "id": str(uuid.uuid4()),
        "document_id": str(uuid.uuid4()),
        "knowledge_base_id": str(uuid.uuid4()),
        "chunk_no": 1,
        "section_no": 1,
        "heading": "第一节",
        "page_no": 2,
        "content": "知识库段落内容",
        "char_start": 0,
        "char_end": 20,
        "token_estimate": 5,
        "embedding_json": json.dumps(embedding),
        "index_generation": 1,
        "is_active": True,
    }
    base.update(overrides)
    return DocumentChunk(**base)  # type: ignore[arg-type]


def test_to_retrieval_chunk_maps_fields() -> None:
    src = _make_chunk()
    row = to_retrieval_chunk(src, doc_title="示例文档")
    assert row.chunk_id == src.id
    assert row.doc_id == src.document_id
    assert row.kb_id == src.knowledge_base_id
    assert row.content == src.content
    assert row.page == 2
    assert row.embedding is not None
    assert len(row.embedding) == 8
    assert row.metadata_["doc_title"] == "示例文档"
    assert row.metadata_["chunk_no"] == 1
    assert row.metadata_["heading"] == "第一节"


def test_build_retrieval_metadata() -> None:
    src = _make_chunk()
    meta = build_retrieval_metadata(src, doc_title="T")
    assert meta["index_generation"] == 1
    assert meta["doc_title"] == "T"


def test_local_embedding_aligns_with_indexer() -> None:
    text = "混合检索对齐"
    indexer = DocumentIndexingService()
    from app.documents.chunking import Chunk

    chunk = Chunk(1, text, None, None, 1, 0, len(text), 4)
    indexed = indexer.embed_chunk(chunk)
    query = deterministic_embedding(text, indexer.settings.embedding_dimensions)
    assert indexed == query
    assert is_local_embedding(None)
    assert is_local_embedding(LOCAL_EMBEDDING_MODEL_ID)
    assert not is_local_embedding("model-uuid")


def test_embedding_literal_format() -> None:
    assert _embedding_literal([1.0, -0.5]) == "[1.0,-0.5]"


def test_row_to_hit_keeps_kb_and_title() -> None:
    hit = _row_to_hit(
        {
            "doc_id": "d1",
            "chunk_id": "c1",
            "kb_id": "k1",
            "page": 3,
            "score": 0.8,
            "content": "正文",
            "metadata": {"doc_title": "标题"},
        }
    )
    assert hit.kb_id == "k1"
    assert hit.doc_title == "标题"
    assert hit.text == "正文"
