# 系统概览路由
# 员工3 负责

import uuid

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.common.database import get_db
from app.common.models import User
from app.common.schemas import APIResponse
from app.users.dashboard_service import get_dashboard_metrics

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["dashboard"])


@router.get("/admin/dashboard")
async def dashboard_endpoint(
    _user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.dashboard.view")),
    db: AsyncSession = Depends(get_db),
):
    """系统概览（管理员权限）
    返回用户、角色等核心指标
    """
    request_id = str(uuid.uuid4())

    metrics = await get_dashboard_metrics(db)

    return APIResponse(
        code=0,
        message="success",
        data=metrics.model_dump(),
        request_id=request_id,
    )
