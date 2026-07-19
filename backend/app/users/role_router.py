# 角色管理路由
# 员工3 负责
# 对应 OpenAPI：GET/POST /roles、PATCH/DELETE /roles/{role_id}、PUT /roles/{role_id}/permissions

import uuid

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.common.database import get_db
from app.common.models import User
from app.common.schemas import APIResponse
from app.users.role_schemas import (
    CreateRoleRequest,
    SetRolePermissionsRequest,
    UpdateRoleRequest,
)
from app.users.role_service import (
    create_role,
    delete_role,
    get_role,
    list_permissions,
    list_roles,
    set_role_permissions,
    update_role,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["roles"])


@router.get("/permissions")
async def list_permissions_endpoint(
    module: str | None = Query(None),
    _user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.role.view")),
    db: AsyncSession = Depends(get_db),
):
    """获取权限码列表，用于角色授权配置。"""
    request_id = str(uuid.uuid4())
    permissions = await list_permissions(db, module=module)
    return APIResponse(
        code=0,
        message="success",
        data=[item.model_dump() for item in permissions],
        request_id=request_id,
    )


# ============================================================
# GET /api/v1/roles — 角色列表
# ============================================================
@router.get("/roles")
async def list_roles_endpoint(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.role.view")),
    db: AsyncSession = Depends(get_db),
):
    """获取角色列表（管理员权限）"""
    request_id = str(uuid.uuid4())

    items, total = await list_roles(db, page=page, page_size=page_size)

    return APIResponse(
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


# ============================================================
# POST /api/v1/roles — 创建角色
# ============================================================
@router.post("/roles", status_code=201)
async def create_role_endpoint(
    body: CreateRoleRequest,
    _user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.role.create")),
    db: AsyncSession = Depends(get_db),
):
    """创建角色（管理员权限）"""
    request_id = str(uuid.uuid4())

    role = await create_role(db, body)

    return APIResponse(
        code=0,
        message="创建成功",
        data=role.model_dump(),
        request_id=request_id,
    )


# ============================================================
# GET /api/v1/roles/{role_id} — 角色详情
# ============================================================
@router.get("/roles/{role_id}")
async def get_role_endpoint(
    role_id: str,
    _user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.role.view")),
    db: AsyncSession = Depends(get_db),
):
    """获取角色详情（管理员权限）"""
    request_id = str(uuid.uuid4())

    role = await get_role(db, role_id)

    return APIResponse(
        code=0,
        message="success",
        data=role.model_dump(),
        request_id=request_id,
    )


# ============================================================
# PATCH /api/v1/roles/{role_id} — 更新角色
# ============================================================
@router.patch("/roles/{role_id}")
async def update_role_endpoint(
    role_id: str,
    body: UpdateRoleRequest,
    _user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.role.edit")),
    db: AsyncSession = Depends(get_db),
):
    """更新角色（管理员权限）"""
    request_id = str(uuid.uuid4())

    role = await update_role(db, role_id, body)

    return APIResponse(
        code=0,
        message="更新成功",
        data=role.model_dump(),
        request_id=request_id,
    )


# ============================================================
# DELETE /api/v1/roles/{role_id} — 删除角色
# ============================================================
@router.delete("/roles/{role_id}")
async def delete_role_endpoint(
    role_id: str,
    _user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.role.delete")),
    db: AsyncSession = Depends(get_db),
):
    """删除角色（管理员权限）"""
    request_id = str(uuid.uuid4())

    await delete_role(db, role_id)

    return APIResponse(
        code=0,
        message="删除成功",
        data=None,
        request_id=request_id,
    )


# ============================================================
# PUT /api/v1/roles/{role_id}/permissions — 设置角色权限
# ============================================================
@router.put("/roles/{role_id}/permissions")
async def set_permissions_endpoint(
    role_id: str,
    body: SetRolePermissionsRequest,
    _user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.role.edit")),
    db: AsyncSession = Depends(get_db),
):
    """设置角色权限（管理员权限）"""
    request_id = str(uuid.uuid4())

    role = await set_role_permissions(db, role_id, body)

    return APIResponse(
        code=0,
        message="权限设置成功",
        data=role.model_dump(),
        request_id=request_id,
    )
