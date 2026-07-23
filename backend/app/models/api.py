"""模型管理路由（提示词 01）"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.common.database import get_db
from app.common.models import User
from app.common.schemas import APIResponse
from app.models import service
from app.models.repository import Model, ModelProvider
from app.models.schemas import (
    ModelCreate,
    ModelProviderCreate,
    ModelProviderUpdate,
    ModelUpdate,
)
from app.rag._shared.audit_helper import audit

router = APIRouter(prefix="/api/v1/models", tags=["models"])


def _to_provider_response(p: ModelProvider) -> dict[str, object]:
    return {
        "code": p.code,
        "display_name": p.display_name,
        "base_url": p.base_url,
        "enabled": p.enabled,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }


def _to_model_response(m: Model) -> dict[str, object]:
    return {
        "id": m.id,
        "provider_code": m.provider_code,
        "model_name": m.model_name,
        "kind": m.kind,
        "parameters": m.parameters or {},
        "api_key_set": bool(m.api_key_encrypted),
        "dimensions": m.dimensions,
        "distance": m.distance,
        "top_n": m.top_n,
        "enabled": m.enabled,
        "created_at": m.created_at,
        "updated_at": m.updated_at,
    }


# Providers
@router.get("/providers")
async def list_providers_endpoint(
    request: Request,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.model.view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    providers = await service.list_providers(db)
    return APIResponse(data=[_to_provider_response(p) for p in providers]).model_dump()


@router.post("/providers", status_code=status.HTTP_201_CREATED)
async def upsert_provider_endpoint(
    request: Request,
    payload: ModelProviderCreate,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.model.create")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    provider = await service.upsert_provider(db, payload)
    await db.commit()
    await audit(
        db,
        action="model_provider_upsert",
        user_id=user.id,
        resource_type="model_provider",
        resource_id=provider.code,
        request=request,
    )
    await db.commit()
    await db.refresh(provider)
    return APIResponse(data=_to_provider_response(provider)).model_dump()


@router.patch("/providers/{code}")
async def patch_provider_endpoint(
    code: str,
    request: Request,
    payload: ModelProviderUpdate,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.model.edit")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    provider = await service.patch_provider(db, code, payload)
    await db.commit()
    await audit(
        db, action="model_provider_patch", user_id=user.id, resource_id=code, request=request
    )
    await db.commit()
    await db.refresh(provider)
    return APIResponse(data=_to_provider_response(provider)).model_dump()


@router.delete("/providers/{code}")
async def delete_provider_endpoint(
    code: str,
    request: Request,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.model.delete")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    await service.delete_provider(db, code)
    await db.commit()
    await audit(
        db, action="model_provider_delete", user_id=user.id, resource_id=code, request=request
    )
    await db.commit()
    return APIResponse().model_dump()


# Models
@router.get("")
async def list_models_endpoint(
    request: Request,
    provider_code: str | None = None,
    kind: str | None = None,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.model.view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    models = await service.list_models(db, provider_code=provider_code, kind=kind)
    return APIResponse(data=[_to_model_response(m) for m in models]).model_dump()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_model_endpoint(
    request: Request,
    payload: ModelCreate,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.model.create")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    model = await service.create_model(db, payload)
    await db.commit()
    await audit(
        db,
        action="model_create",
        user_id=user.id,
        resource_type="model",
        resource_id=model.id,
        request=request,
    )
    await db.commit()
    await db.refresh(model)
    return APIResponse(data=_to_model_response(model)).model_dump()


@router.patch("/{model_id}")
async def patch_model_endpoint(
    model_id: str,
    request: Request,
    payload: ModelUpdate,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.model.edit")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    model = await service.update_model(db, model_id, payload)
    await db.commit()
    await audit(db, action="model_patch", user_id=user.id, resource_id=model_id, request=request)
    await db.commit()
    await db.refresh(model)
    return APIResponse(data=_to_model_response(model)).model_dump()


@router.delete("/{model_id}")
async def delete_model_endpoint(
    model_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.model.delete")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    await service.delete_model(db, model_id)
    await db.commit()
    await audit(db, action="model_delete", user_id=user.id, resource_id=model_id, request=request)
    await db.commit()
    return APIResponse().model_dump()


@router.post("/{model_id}/test")
async def test_model_endpoint(
    model_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.model.edit")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    result = await service.test_model(db, model_id)
    await audit(
        db,
        action="model_test",
        user_id=user.id,
        resource_id=model_id,
        result="success" if result.ok else "failure",
        request=request,
    )
    await db.commit()
    return APIResponse(data=result.model_dump()).model_dump()
