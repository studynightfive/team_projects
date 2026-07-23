"""模型管理业务逻辑（提示词 01 §四）

提供：
- provider CRUD：get_provider / list_providers / upsert_provider / delete_provider
- model CRUD：list / get / create / update / delete
- 密钥加解密：写入时 Fernet 加密，读取时仅返回 api_key_set 标志
- 连通性测试：test_model 真实调用 provider
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from time import perf_counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import settings
from app.common.exceptions import ConflictException, NotFoundException, ValidationException
from app.models.providers.openai import build_provider, validate_provider_base_url
from app.models.repository import Model, ModelProvider
from app.models.schemas import (
    ModelCreate,
    ModelProviderCreate,
    ModelProviderUpdate,
    ModelUpdate,
    TestModelResponse,
)
from app.models.security import decrypt_api_key, encrypt_api_key


# ============================================================
# Provider CRUD
# ============================================================
def _validate_provider_base_url(code: str, base_url: str) -> None:
    validate_provider_base_url(code, base_url)


async def list_providers(db: AsyncSession) -> Sequence[ModelProvider]:
    res = await db.execute(select(ModelProvider).order_by(ModelProvider.code))
    return res.scalars().all()


async def get_provider(db: AsyncSession, code: str) -> ModelProvider | None:
    return await db.get(ModelProvider, code)


async def upsert_provider(db: AsyncSession, payload: ModelProviderCreate) -> ModelProvider:
    _validate_provider_base_url(payload.code, payload.base_url)
    existing = await get_provider(db, payload.code)
    if existing is None:
        provider = ModelProvider(
            code=payload.code,
            display_name=payload.display_name,
            base_url=payload.base_url,
            enabled=payload.enabled,
        )
        db.add(provider)
        return provider
    existing.display_name = payload.display_name
    existing.base_url = payload.base_url
    existing.enabled = payload.enabled
    return existing


async def patch_provider(
    db: AsyncSession, code: str, payload: ModelProviderUpdate
) -> ModelProvider:
    existing = await get_provider(db, code)
    if existing is None:
        raise NotFoundException()
    if payload.base_url is not None:
        _validate_provider_base_url(code, payload.base_url)
    for field in ("display_name", "base_url", "enabled"):
        v = getattr(payload, field, None)
        if v is not None:
            setattr(existing, field, v)
    return existing


async def delete_provider(db: AsyncSession, code: str) -> None:
    provider = await get_provider(db, code)
    if provider is None:
        raise NotFoundException()
    res = await db.execute(select(Model).where(Model.provider_code == code).limit(1))
    if res.scalar_one_or_none() is not None:
        raise ConflictException(code=40901, message="该 provider 仍有模型记录，无法删除")
    await db.delete(provider)


# ============================================================
# Model CRUD
# ============================================================
async def list_models(
    db: AsyncSession, *, provider_code: str | None = None, kind: str | None = None
) -> Sequence[Model]:
    q = select(Model)
    if provider_code:
        q = q.where(Model.provider_code == provider_code)
    if kind:
        q = q.where(Model.kind == kind)
    q = q.order_by(Model.provider_code, Model.model_name)
    res = await db.execute(q)
    return res.scalars().all()


async def get_model(db: AsyncSession, model_id: str) -> Model | None:
    return await db.get(Model, model_id)


async def create_model(db: AsyncSession, payload: ModelCreate) -> Model:
    if await get_provider(db, payload.provider_code) is None:
        raise ValidationException(message="provider_code 不存在")
    encrypted = encrypt_api_key(payload.api_key) if payload.api_key else None
    model = Model(
        id=str(uuid.uuid4()),
        provider_code=payload.provider_code,
        model_name=payload.model_name,
        kind=payload.kind,
        parameters=payload.parameters,
        api_key_encrypted=encrypted,
        dimensions=payload.dimensions,
        distance=payload.distance,
        top_n=payload.top_n,
        enabled=payload.enabled,
    )
    db.add(model)
    return model


async def update_model(db: AsyncSession, model_id: str, payload: ModelUpdate) -> Model:
    model = await get_model(db, model_id)
    if model is None:
        raise NotFoundException()
    for f in ("model_name", "parameters", "enabled", "dimensions", "distance", "top_n"):
        v = getattr(payload, f, None)
        if v is not None:
            setattr(model, f, v)
    if payload.api_key is not None:
        model.api_key_encrypted = encrypt_api_key(payload.api_key) if payload.api_key else None
    return model


async def delete_model(db: AsyncSession, model_id: str) -> None:
    model = await get_model(db, model_id)
    if model is None:
        raise NotFoundException()
    await db.delete(model)


# ============================================================
# 连通性测试
# ============================================================
async def test_model(db: AsyncSession, model_id: str) -> TestModelResponse:
    model = await get_model(db, model_id)
    if model is None:
        raise NotFoundException()
    provider = await get_provider(db, model.provider_code)
    if provider is None or not provider.enabled:
        raise NotFoundException()
    _validate_provider_base_url(provider.code, provider.base_url)
    api_key = decrypt_api_key(model.api_key_encrypted) if model.api_key_encrypted else ""
    if provider.code != "ollama" and not api_key.strip():
        return TestModelResponse(
            ok=False,
            latency_ms=0,
            error_code="missing_api_key",
            error_message="请先保存 API Key 后再测试模型",
        )

    started_at = perf_counter()
    client = build_provider(
        provider.code,
        provider.base_url,
        api_key,
        timeout=settings.model_provider_timeout_seconds,
    )
    model_info: dict[str, object] = {
        "model_name": model.model_name,
        "kind": model.kind,
        "invoked": True,
    }
    try:
        if model.kind == "chat":
            configured_max_tokens = (model.parameters or {}).get("max_tokens")
            max_tokens = (
                min(max(configured_max_tokens, 512), 8192)
                if isinstance(configured_max_tokens, int)
                and not isinstance(configured_max_tokens, bool)
                else max(settings.rag_answer_max_tokens, 512)
            )
            answer = await client.chat(
                model_name=model.model_name,
                messages=[{"role": "user", "content": "只回答：连接正常"}],
                temperature=0.2,
                max_tokens=max_tokens,
                stream=False,
                timeout=settings.model_provider_timeout_seconds,
            )
            if not isinstance(answer, str) or not answer.strip():
                return TestModelResponse(
                    ok=False,
                    latency_ms=int((perf_counter() - started_at) * 1000),
                    error_code="empty_response",
                    error_message="模型调用成功但没有返回可见答案，请检查模型标识和最大输出 Token",
                )
            model_info["response_chars"] = len(answer)
        elif model.kind == "embedding":
            vectors = await client.embed(
                model_name=model.model_name,
                inputs=["医疗信息化模型连通性测试"],
                timeout=settings.model_provider_timeout_seconds,
            )
            if len(vectors) != 1 or not vectors[0]:
                return TestModelResponse(
                    ok=False,
                    latency_ms=int((perf_counter() - started_at) * 1000),
                    error_code="empty_embedding",
                    error_message="Embedding 模型未返回有效向量",
                )
            returned_dimensions = len(vectors[0])
            if model.dimensions is not None and returned_dimensions != model.dimensions:
                return TestModelResponse(
                    ok=False,
                    latency_ms=int((perf_counter() - started_at) * 1000),
                    error_code="dimension_mismatch",
                    error_message=(
                        f"Embedding 返回 {returned_dimensions} 维，"
                        f"与配置的 {model.dimensions} 维不一致"
                    ),
                )
            model_info["dimensions"] = returned_dimensions
        elif model.kind == "rerank":
            results = await client.rerank(
                model_name=model.model_name,
                query="医疗数据安全",
                documents=["医疗数据需要访问控制和审计"],
                top_n=1,
                timeout=settings.model_provider_timeout_seconds,
            )
            if not results:
                return TestModelResponse(
                    ok=False,
                    latency_ms=int((perf_counter() - started_at) * 1000),
                    error_code="empty_rerank",
                    error_message="Rerank 模型未返回有效排序结果",
                )
            model_info["result_count"] = len(results)
        else:
            raise ValidationException(message="不支持的模型类型")
    except ValidationException:
        raise
    except Exception as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        if status_code in (401, 403):
            error_code = "authentication_failed"
            error_message = "模型服务认证失败，请检查 API Key"
        elif status_code == 404:
            error_code = "model_not_found"
            error_message = "模型标识不存在或当前账号未开通该模型"
        elif status_code == 429:
            error_code = "rate_limited"
            error_message = "模型服务请求受限，请稍后重试"
        else:
            error_code = "model_invocation_failed"
            error_message = f"模型真实调用失败（{status_code or type(exc).__name__}）"
        return TestModelResponse(
            ok=False,
            latency_ms=int((perf_counter() - started_at) * 1000),
            error_code=error_code,
            error_message=error_message,
        )

    return TestModelResponse(
        ok=True,
        latency_ms=int((perf_counter() - started_at) * 1000),
        model_info=model_info,
    )
