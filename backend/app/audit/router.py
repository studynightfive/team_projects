# 审计日志路由
# 员工3 负责
# 对应 OpenAPI：GET /audit-logs

import uuid
from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import list_audit_logs
from app.auth.dependencies import get_current_user, require_permission
from app.common.database import get_db
from app.common.models import User
from app.common.schemas import APIResponse

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["audit"])


@router.get("/audit-logs")
async def audit_logs_endpoint(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str | None = Query(None),
    action: str | None = Query(None),
    resource_type: str | None = Query(None),
    resource_id: str | None = Query(None),
    result: str | None = Query(None),
    created_after: datetime | None = Query(None),
    created_before: datetime | None = Query(None),
    _user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.audit.view")),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict[str, object]]:
    """获取审计日志列表（管理员权限）
    方案第15.5节：审计日志不展示 Secret 和敏感请求体
    """
    request_id = str(uuid.uuid4())

    items, total = await list_audit_logs(
        db,
        page=page,
        page_size=page_size,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        result=result,
        created_after=created_after,
        created_before=created_before,
    )

    return APIResponse[dict[str, object]](
        code=0,
        message="success",
        data={
            "items": [item.model_dump() for item in items],
            "page": page,
            "page_size": page_size,
            "total": total,
        },
        request_id=request_id,
    )
