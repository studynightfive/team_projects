# 认证模块请求/响应模型
# 员工3 负责
# 对应 OpenAPI：/auth/login、/auth/logout、/auth/refresh、/me

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# ============================================================
# 请求模型
# ============================================================
class LoginRequest(BaseModel):
    """登录请求"""

    username: str = Field(..., min_length=1, max_length=150)
    password: str = Field(..., min_length=1, max_length=128)


# ============================================================
# 响应数据模型
# ============================================================
class UserRoleData(BaseModel):
    """角色简要信息"""

    id: str
    name: str

    model_config = {"from_attributes": True}


class KnowledgeBaseAccessData(BaseModel):
    """知识库数据权限"""

    kb_id: str
    access_level: str

    model_config = {"from_attributes": True}


class MeData(BaseModel):
    """当前用户信息（/me 返回）"""

    id: str
    username: str
    display_name: str
    roles: list[UserRoleData] = []
    permissions: list[str] = []
    knowledge_base_access: list[KnowledgeBaseAccessData] = []

    model_config = {"from_attributes": True}


class LoginData(BaseModel):
    """登录成功返回的 Token 数据"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: MeData


# ============================================================
# Token 载荷
# ============================================================
class TokenPayload(BaseModel):
    """JWT Token 内部载荷"""

    sub: str
    permissions: list[str] = []
    type: str = "access"
    iat: datetime | None = None
    exp: datetime | None = None
    jti: str | None = None
