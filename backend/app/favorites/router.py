"""用户收藏接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_any_permission
from app.common.database import get_db
from app.common.exceptions import ForbiddenException, NotFoundException
from app.common.models import User
from app.common.schemas import APIResponse, PaginatedData
from app.favorites.models import Favorite
from app.favorites.schemas import FavoriteCreate, FavoriteResponse, FavoriteUpdate
from app.rag._shared.audit_helper import audit

router = APIRouter(prefix="/api/v1/favorites", tags=["favorites"])


def _normalize_tags(tags: list[str]) -> list[str]:
    normalized: list[str] = []
    for tag in tags:
        value = tag.strip()
        if not value or value in normalized:
            continue
        normalized.append(value[:24])
        if len(normalized) >= 12:
            break
    return normalized


@router.get("")
async def list_favorites_endpoint(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_any_permission("favorite:read", "chat.use")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    base = select(Favorite).where(Favorite.user_id == user.id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    result = await db.execute(
        base.order_by(Favorite.saved_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [FavoriteResponse.model_validate(item).model_dump() for item in result.scalars()]
    return APIResponse(
        data=PaginatedData(items=items, page=page, page_size=page_size, total=total).model_dump()
    ).model_dump()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_favorite_endpoint(
    request: Request,
    payload: FavoriteCreate,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_any_permission("favorite:write", "chat.use")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    favorite = Favorite(
        user_id=user.id,
        type=payload.type,
        title=payload.title.strip(),
        summary=payload.summary.strip(),
        tags=_normalize_tags(payload.tags),
        note=payload.note.strip(),
        source_id=payload.source_id,
        source_payload=payload.source_payload,
    )
    db.add(favorite)
    await db.flush()
    await audit(
        db,
        action="favorite_create",
        user_id=user.id,
        resource_type="favorite",
        resource_id=favorite.id,
        request=request,
    )
    await db.commit()
    await db.refresh(favorite)
    return APIResponse(data=FavoriteResponse.model_validate(favorite).model_dump()).model_dump()


@router.patch("/{favorite_id}")
async def update_favorite_endpoint(
    favorite_id: str,
    payload: FavoriteUpdate,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_any_permission("favorite:write", "chat.use")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    favorite = await db.get(Favorite, favorite_id)
    if favorite is None:
        raise NotFoundException()
    if favorite.user_id != user.id:
        raise ForbiddenException(message="无权访问此收藏")

    if payload.note is not None:
        favorite.note = payload.note.strip()
    if payload.tags is not None:
        favorite.tags = _normalize_tags(payload.tags)
    await db.commit()
    await db.refresh(favorite)
    return APIResponse(data=FavoriteResponse.model_validate(favorite).model_dump()).model_dump()


@router.delete("/{favorite_id}")
async def delete_favorite_endpoint(
    favorite_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_any_permission("favorite:write", "chat.use")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    favorite = await db.get(Favorite, favorite_id)
    if favorite is None:
        raise NotFoundException()
    if favorite.user_id != user.id:
        raise ForbiddenException(message="无权访问此收藏")

    await db.delete(favorite)
    await audit(
        db,
        action="favorite_delete",
        user_id=user.id,
        resource_type="favorite",
        resource_id=favorite_id,
        request=request,
    )
    await db.commit()
    return APIResponse().model_dump()
