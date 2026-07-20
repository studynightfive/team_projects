# 用户管理路由
# 员工3 负责
# 对应 OpenAPI：GET/POST /users、PATCH /users/{user_id}、POST /users/{user_id}/reset-password

import uuid

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.common.database import get_db
from app.common.models import User
from app.common.schemas import APIResponse
from app.users.schemas import (
    CreateUserRequest,
    ResetPasswordRequest,
    UpdateUserRequest,
)
from app.users.service import (
    create_user,
    list_users,
    reset_user_password,
    update_user,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["users"])


# ============================================================
# GET /api/v1/users — 用户列表
# ============================================================
@router.get("/users")
async def list_users_endpoint(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    status: str | None = Query(None),
    _user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.user.view")),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict[str, object]]:
    """获取用户列表（管理员权限）"""
    request_id = str(uuid.uuid4())

    items, total = await list_users(db, page=page, page_size=page_size,
                                    search=search, status=status)

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


# ============================================================
# POST /api/v1/users — 创建用户
# ============================================================
@router.post("/users", status_code=201)
async def create_user_endpoint(
    body: CreateUserRequest,
    _user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.user.create")),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict[str, object]]:
    """创建用户（管理员权限）"""
    request_id = str(uuid.uuid4())

    user = await create_user(db, body)

    return APIResponse[dict[str, object]](
        code=0,
        message="创建成功",
        data=user.model_dump(),
        request_id=request_id,
    )


# ============================================================
# PATCH /api/v1/users/{user_id} — 更新用户
# ============================================================
@router.patch("/users/{user_id}")
async def update_user_endpoint(
    user_id: str,
    body: UpdateUserRequest,
    _current_user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.user.edit")),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict[str, object]]:
    """更新用户（管理员权限）"""
    request_id = str(uuid.uuid4())

    user = await update_user(db, user_id, body)

    return APIResponse[dict[str, object]](
        code=0,
        message="更新成功",
        data=user.model_dump(),
        request_id=request_id,
    )


# ============================================================
# POST /api/v1/users/{user_id}/reset-password — 重置密码
# ============================================================
@router.post("/users/{user_id}/reset-password")
async def reset_password_endpoint(
    user_id: str,
    body: ResetPasswordRequest,
    _current_user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("admin.user.edit")),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[None]:
    """重置用户密码（管理员权限）
    方案第5.3节：密码重置不返回旧密码
    """
    request_id = str(uuid.uuid4())

    await reset_user_password(db, user_id, body.new_password)

    return APIResponse[None](
        code=0,
        message="密码重置成功",
        data=None,
        request_id=request_id,
    )
