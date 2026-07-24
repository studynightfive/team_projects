"""业务看板与用户激励路由。"""

from __future__ import annotations

import uuid
from enum import IntEnum
from typing import Literal, cast

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.common.database import get_db
from app.common.models import User
from app.common.schemas import APIResponse
from app.users.dashboard_schemas import DashboardMetrics, UserIncentives
from app.users.dashboard_service import (
    get_dashboard_metrics,
    get_user_incentives,
)

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


class DashboardDays(IntEnum):
    SEVEN = 7
    THIRTY = 30
    NINETY = 90


class DashboardPageSize(IntEnum):
    TEN = 10
    TWENTY = 20
    FIFTY = 50


def _request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    return request_id if isinstance(request_id, str) and request_id else str(uuid.uuid4())


@router.get(
    "/admin/dashboard",
    response_model=APIResponse[DashboardMetrics],
)
async def dashboard_endpoint(
    request: Request,
    days: DashboardDays = Query(default=DashboardDays.THIRTY),
    department_id: str | None = Query(default=None),
    leaderboard_page: int = Query(default=1, ge=1),
    leaderboard_page_size: DashboardPageSize = Query(
        default=DashboardPageSize.TEN
    ),
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.dashboard.view")),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[DashboardMetrics]:
    metrics = await get_dashboard_metrics(
        db,
        user=user,
        days=cast(Literal[7, 30, 90], int(days)),
        department_id=department_id,
        leaderboard_page=leaderboard_page,
        leaderboard_page_size=int(leaderboard_page_size),
    )
    return APIResponse(
        data=metrics,
        request_id=_request_id(request),
    )


@router.get(
    "/me/incentives",
    response_model=APIResponse[UserIncentives],
)
async def my_incentives_endpoint(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: DashboardPageSize = Query(default=DashboardPageSize.TEN),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[UserIncentives]:
    incentives = await get_user_incentives(
        db,
        user=user,
        page=page,
        page_size=int(page_size),
    )
    return APIResponse(
        data=incentives,
        request_id=_request_id(request),
    )
