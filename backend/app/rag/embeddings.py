"""统一 embedding 入口：入库索引与检索查询共用，避免 stub/真实模型维度漂移。

- embedding_model_id 为 None / \"local\" → deterministic_embedding（离线可测）
- 否则按 models 表配置走 OpenAI 兼容 Provider.embed
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import settings
from app.documents.indexing import deterministic_embedding
from app.models import service as model_service
from app.models.providers.openai import build_provider
from app.models.security import decrypt_api_key

LOCAL_EMBEDDING_MODEL_ID = "local"
_EMBED_BATCH_SIZE = 32


def is_local_embedding(model_id: str | None) -> bool:
    return model_id is None or model_id == "" or model_id == LOCAL_EMBEDDING_MODEL_ID


def resolve_indexing_model_id(explicit: str | None = None) -> str:
    """入库用模型：显式参数优先，否则读 INDEXING_EMBEDDING_MODEL_ID。"""
    if explicit is not None and explicit != "":
        return explicit
    configured = settings.indexing_embedding_model_id
    return configured if configured else LOCAL_EMBEDDING_MODEL_ID


async def embed_texts(
    db: AsyncSession,
    texts: list[str],
    *,
    embedding_model_id: str | None,
) -> list[list[float]]:
    """批量向量化；保持与单条查询同一模型选择逻辑。"""
    if not texts:
        return []
    if is_local_embedding(embedding_model_id):
        dims = settings.embedding_dimensions
        return [deterministic_embedding(t, dims) for t in texts]

    model = await model_service.get_model(db, embedding_model_id)  # type: ignore[arg-type]
    if model is None or model.kind != "embedding" or not model.enabled:
        raise ValueError("embedding model not found or disabled")
    provider = await model_service.get_provider(db, model.provider_code)
    if provider is None or not provider.enabled:
        raise ValueError("embedding provider not found or disabled")
    api_key = decrypt_api_key(model.api_key_encrypted) if model.api_key_encrypted else ""
    if not api_key and settings.model_api_key:
        api_key = settings.model_api_key
    p = build_provider(provider.code, provider.base_url, api_key)

    out: list[list[float]] = []
    for i in range(0, len(texts), _EMBED_BATCH_SIZE):
        batch = texts[i : i + _EMBED_BATCH_SIZE]
        vectors = await p.embed(model_name=model.model_name, inputs=batch)
        if len(vectors) != len(batch):
            raise ValueError("embedding provider returned unexpected batch size")
        out.extend(vectors)
    return out


async def embed_query(
    db: AsyncSession,
    *,
    query: str,
    embedding_model_id: str | None,
) -> list[float]:
    vectors = await embed_texts(db, [query], embedding_model_id=embedding_model_id)
    return vectors[0]


def embedding_literal(values: list[float]) -> str:
    """pgvector 文本字面量，避免 ARRAY 绑定与 <=> 类型不匹配。"""
    return "[" + ",".join(str(float(v)) for v in values) + "]"
