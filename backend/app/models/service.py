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

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
    if provider is None:
        raise NotFoundException()
    _validate_provider_base_url(provider.code, provider.base_url)
    api_key = decrypt_api_key(model.api_key_encrypted) if model.api_key_encrypted else ""
    p = build_provider(provider.code, provider.base_url, api_key)
    result = await p.test(model_name=model.model_name, api_key=api_key, base_url=provider.base_url)
    return TestModelResponse.model_validate(result)
