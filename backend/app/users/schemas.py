# 用户管理请求/响应模型
# 员工3 负责
# 对应 OpenAPI：/users、/users/{user_id}、/users/{user_id}/reset-password

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# ============================================================
# 请求模型
# ============================================================
class CreateUserRequest(BaseModel):
    """创建用户请求"""

    username: str = Field(..., min_length=1, max_length=150)
    display_name: str = Field(..., min_length=1, max_length=150)
    password: str = Field(..., min_length=7, max_length=128)
    role_ids: list[str] = []


class UpdateUserRequest(BaseModel):
    """更新用户请求"""

    status: str | None = None  # active, disabled
    role_ids: list[str] | None = None

    model_config = {"extra": "forbid"}


class ResetPasswordRequest(BaseModel):
    """重置密码请求"""

    new_password: str = Field(..., min_length=7, max_length=128)


# ============================================================
# 响应数据模型
# ============================================================
class UserResponse(BaseModel):
    """用户响应（不含密码哈希）"""

    id: str
    username: str
    display_name: str
    status: str
    roles: list[RoleBrief] = []
    last_login_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class RoleBrief(BaseModel):
    """角色简要信息"""

    id: str
    name: str

    model_config = {"from_attributes": True}


class UserListItem(BaseModel):
    """用户列表项"""

    id: str
    username: str
    display_name: str
    status: str
    roles: list[RoleBrief] = []
    last_login_at: datetime | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
