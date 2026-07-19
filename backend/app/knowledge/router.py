"""知识库 API 路由。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.common.database import get_db
from app.common.models import User
from app.common.schemas import APIResponse, PaginatedData
from app.knowledge import service
from app.knowledge.schemas import KnowledgeBaseCreate, KnowledgeBaseUpdate

router = APIRouter(prefix="/api/v1/knowledge-bases", tags=["knowledge-bases"])


@router.get("")
async def list_knowledge_bases(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items, total = await service.list_knowledge_bases(
        db,
        user,
        page=page,
        page_size=page_size,
    )
    return APIResponse(
        data=PaginatedData(items=items, page=page, page_size=page_size, total=total),
        request_id=str(uuid.uuid4()),
    )


@router.get("/available")
async def list_available_knowledge_bases(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items, total = await service.list_knowledge_bases(
        db,
        user,
        page=1,
        page_size=100,
        active_only=True,
    )
    return APIResponse(
        data=PaginatedData(items=items, page=1, page_size=100, total=total),
        request_id=str(uuid.uuid4()),
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    payload: KnowledgeBaseCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await service.create_knowledge_base(db, user, payload)
    return APIResponse(data=data, request_id=str(uuid.uuid4()))


@router.patch("/{kb_id}")
async def update_knowledge_base(
    kb_id: str,
    payload: KnowledgeBaseUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await service.update_knowledge_base(db, user, kb_id, payload)
    return APIResponse(data=data, request_id=str(uuid.uuid4()))
