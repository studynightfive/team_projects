"""Full-text preparation and deterministic embedding stubs for indexing."""

from __future__ import annotations

import hashlib
import json
import math
import re

from app.common.config import Settings
from app.common.config import settings as app_settings
from app.documents.chunking import Chunk

_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def deterministic_embedding(text: str, dimensions: int) -> list[float]:
    """Local deterministic pseudo-embedding for offline indexing tests.

    Employee 5 replaces this with the configured embedding model while keeping
    the DocumentIndexingService public interface stable.
    """
    vec = [0.0] * dimensions
    tokens = tokenize(text) or ["empty"]
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        for i in range(dimensions):
            byte = digest[i % len(digest)]
            vec[i] += ((byte / 255.0) * 2.0) - 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class DocumentIndexingService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings if settings is not None else app_settings

    def build_search_document(self, chunk: Chunk, *, document_id: str, title: str) -> dict:
        tokens = tokenize(chunk.content)
        return {
            "document_id": document_id,
            "title": title,
            "chunk_no": chunk.chunk_no,
            "heading": chunk.heading,
            "page_no": chunk.page_no,
            "content": chunk.content,
            "tokens": tokens,
            "lexeme": " ".join(tokens),
        }

    def embed_chunk(self, chunk: Chunk) -> list[float]:
        return deterministic_embedding(chunk.content, self.settings.embedding_dimensions)

    def serialize_embedding(self, values: list[float]) -> str:
        return json.dumps(values)

    def deserialize_embedding(self, payload: str | None) -> list[float] | None:
        if not payload:
            return None
        return list(json.loads(payload))
