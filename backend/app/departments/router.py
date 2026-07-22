"""部门管理 API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.common.database import get_db
from app.common.models import User
from app.common.schemas import APIResponse
from app.departments import service
from app.departments.schemas import (
    DepartmentCreate,
    DepartmentListResponse,
    DepartmentResponse,
    DepartmentUpdate,
)
from app.rag._shared.audit_helper import audit

router = APIRouter(prefix="/api/v1/departments", tags=["departments"])


@router.get("")
async def list_departments_endpoint(
    _user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.department.view")),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[DepartmentListResponse]:
    items = await service.list_departments(db)
    return APIResponse(data=DepartmentListResponse(items=items, total=len(items)))


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_department_endpoint(
    request: Request,
    payload: DepartmentCreate,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.department.manage")),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[DepartmentResponse]:
    item = await service.create_department(db, payload)
    await audit(
        db,
        action="department_create",
        user_id=user.id,
        resource_type="department",
        resource_id=item.id,
        request=request,
    )
    await db.commit()
    return APIResponse(data=item)


@router.patch("/{department_id}")
async def update_department_endpoint(
    department_id: str,
    request: Request,
    payload: DepartmentUpdate,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.department.manage")),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[DepartmentResponse]:
    item = await service.update_department(db, department_id, payload)
    await audit(
        db,
        action="department_update",
        user_id=user.id,
        resource_type="department",
        resource_id=item.id,
        request=request,
    )
    await db.commit()
    return APIResponse(data=item)
