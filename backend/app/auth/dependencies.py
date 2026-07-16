# 认证依赖注入
# 员工3 负责
# 提供 get_current_user、require_permission 等 FastAPI 依赖

from collections.abc import Callable

import jwt
from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import decode_access_token
from app.common.database import get_db
from app.common.exceptions import (
    ForbiddenException,
    TokenExpiredException,
    TokenInvalidException,
    UnauthorizedException,
    UserDisabledException,
)
from app.common.models import User


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    authorization: str | None = Header(None),
) -> User:
    """从 Authorization 头提取当前用户

    供路由使用：user = Depends(get_current_user)
    """
    token = _extract_token(authorization)
    if token is None:
        raise UnauthorizedException()

    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise TokenExpiredException()
    except jwt.PyJWTError:
        raise TokenInvalidException()

    if payload.get("type") != "access":
        raise TokenInvalidException()

    user_id = payload.get("sub")
    if not user_id:
        raise TokenInvalidException()

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise UnauthorizedException()

    if user.status == "disabled":
        raise UserDisabledException()

    return user


async def get_current_user_id(
    authorization: str | None = Header(None),
) -> str:
    """仅提取当前用户 ID（不查询数据库）

    用于轻量级场景，确保请求携带有效 Token
    """
    token = _extract_token(authorization)
    if token is None:
        raise UnauthorizedException()

    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise TokenExpiredException()
    except jwt.PyJWTError:
        raise TokenInvalidException()

    if payload.get("type") != "access":
        raise TokenInvalidException()

    user_id = payload.get("sub")
    if not user_id:
        raise TokenInvalidException()

    return user_id


def require_permission(permission_code: str) -> Callable:
    """权限校验依赖工厂

    用法：
        @router.get("/admin/users")
        async def list_users(
            user: User = Depends(get_current_user),
            _: None = Depends(require_permission("admin.user.view")),
        ):
            ...
    """

    async def permission_checker(
        user: User = Depends(get_current_user),
    ) -> None:
        user_permissions: set[str] = set()
        for role in user.roles:
            if role.status != "active":
                continue
            for perm in role.permissions:
                user_permissions.add(perm.code)

        if permission_code not in user_permissions:
            raise ForbiddenException(
                message=f"需要权限: {permission_code}"
            )

    return permission_checker


def require_any_permission(*permission_codes: str) -> Callable:
    """任一权限校验依赖工厂

    用户只需拥有其中之一即可通过
    """

    async def permission_checker(
        user: User = Depends(get_current_user),
    ) -> None:
        user_permissions: set[str] = set()
        for role in user.roles:
            if role.status != "active":
                continue
            for perm in role.permissions:
                user_permissions.add(perm.code)

        if not any(p in user_permissions for p in permission_codes):
            raise ForbiddenException(
                message=f"需要至少一个权限: {permission_codes}"
            )

    return permission_checker


# ============================================================
# 辅助函数
# ============================================================
def _extract_token(authorization: str | None) -> str | None:
    """从 Authorization 头提取 Bearer Token"""
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]
