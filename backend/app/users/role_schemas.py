# 角色管理请求/响应模型
# 员工3 负责
# 对应 OpenAPI：/roles、/roles/{role_id}、/roles/{role_id}/permissions

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# ============================================================
# 请求模型
# ============================================================
class CreateRoleRequest(BaseModel):
    """创建角色请求"""

    name: str = Field(..., min_length=1, max_length=150)
    description: str | None = Field(None, max_length=500)
    permission_ids: list[str] = []


class UpdateRoleRequest(BaseModel):
    """更新角色请求"""

    name: str | None = Field(None, min_length=1, max_length=150)
    description: str | None = Field(None, max_length=500)
    status: str | None = None  # active, disabled


class SetRolePermissionsRequest(BaseModel):
    """设置角色权限请求"""

    permission_ids: list[str] = []


# ============================================================
# 响应数据模型
# ============================================================
class PermissionResponse(BaseModel):
    """权限响应"""

    id: str
    code: str
    name: str
    module: str
    action: str

    model_config = {"from_attributes": True}


class RoleResponse(BaseModel):
    """角色响应"""

    id: str
    name: str
    description: str | None = None
    status: str
    permissions: list[PermissionResponse] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class RoleListItem(BaseModel):
    """角色列表项"""

    id: str
    name: str
    description: str | None = None
    status: str
    permissions_count: int = 0
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
