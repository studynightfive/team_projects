"""检索路由（提示词 02）"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.common.database import get_db
from app.common.models import User
from app.common.schemas import APIResponse
from app.rag._shared.audit_helper import audit
from app.rag.search import service
from app.rag.search.schemas import SearchRequest

router = APIRouter(prefix="/api/v1/retrieval", tags=["retrieval"])


@router.post("/search")
async def search_endpoint(
    request: Request,
    payload: SearchRequest,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("retrieval:read")),
    db: AsyncSession = Depends(get_db),
):
    response = await service.search(db, user=user, req=payload)
    await audit(
        db,
        action="retrieval_search",
        user_id=user.id,
        resource_type="kb",
        resource_id=payload.kb_id,
        detail=f"mode={payload.mode} top_k={payload.top_k}",
        request=request,
    )
    await db.commit()
    return APIResponse(data=response.model_dump()).model_dump()
