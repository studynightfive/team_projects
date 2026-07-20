# 认证路由
# 员工3 负责
# 对应 OpenAPI：POST /auth/login、POST /auth/logout、POST /auth/refresh、GET /me

import uuid

import structlog
from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.schemas import LoginRequest, RegisterRequest, UsernameAvailability
from app.auth.service import get_me, login, logout, refresh_access_token
from app.common.config import settings
from app.common.database import get_db
from app.common.exceptions import AppException, UnauthorizedException
from app.common.models import Role, User
from app.common.schemas import APIResponse, ErrorCode
from app.common.seed import DEFAULT_USER_ROLE_NAME
from app.users.schemas import CreateUserRequest
from app.users.service import create_user

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["auth"])


def _refresh_cookie_max_age() -> int:
    """Cookie 与服务端 Refresh Token 有效期共用同一配置事实来源。"""
    return settings.refresh_token_expire_days * 24 * 3600


@router.get("/auth/check-username")
async def check_username_endpoint(
    username: str,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict[str, object]]:
    """检查账号 ID 是否可注册。"""
    normalized = username.strip()
    existing = None
    if normalized != "":
        result = await db.execute(select(User.id).where(User.username == normalized))
        existing = result.scalar_one_or_none()
    return APIResponse[dict[str, object]](
        code=0,
        message="success",
        data=UsernameAvailability(
            username=normalized,
            available=normalized != "" and existing is None,
        ).model_dump(),
        request_id=str(uuid.uuid4()),
    )


@router.post("/auth/register", status_code=201)
async def register_endpoint(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict[str, object]]:
    """公开注册普通用户账号，创建后进入用户管理列表。"""
    request_id = str(uuid.uuid4())
    role_result = await db.execute(
        select(Role).where(Role.name == DEFAULT_USER_ROLE_NAME)
    )
    user_role = role_result.scalar_one_or_none()
    if user_role is None:
        raise AppException(
            code=ErrorCode.ROLE_NOT_FOUND,
            message="注册服务尚未完成基础角色初始化",
            status_code=503,
            request_id=request_id,
        )
    role_ids = [user_role.id]

    try:
        user = await create_user(
            db,
            CreateUserRequest(
                username=body.username.strip(),
                display_name=body.display_name.strip(),
                password=body.password,
                role_ids=role_ids,
            ),
        )
    except AppException as e:
        e.request_id = request_id
        raise e

    return APIResponse[dict[str, object]](
        code=0,
        message="注册成功",
        data=user.model_dump(),
        request_id=request_id,
    )


# ============================================================
# POST /api/v1/auth/login
# ============================================================
@router.post("/auth/login")
async def login_endpoint(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict[str, object]]:
    """用户登录（方案第5.2节）

    JSON 仅返回 Access Token；Refresh Token 只写入 HttpOnly Cookie，
    不进入 localStorage、URL、响应正文或日志。
    """
    request_id = str(uuid.uuid4())

    try:
        result = await login(db, body.username, body.password)
    except AppException as e:
        e.request_id = request_id
        raise e

    # 设置 Refresh Token 到 HttpOnly Cookie
    response.set_cookie(
        key="refresh_token",
        value=result.refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/api/v1/auth",
        max_age=_refresh_cookie_max_age(),
    )

    return APIResponse[dict[str, object]](
        code=0,
        message="登录成功",
        data={
            "access_token": result.access_token,
            "token_type": result.token_type,
            "user": result.user.model_dump(),
        },
        request_id=request_id,
    )


# ============================================================
# POST /api/v1/auth/logout
# ============================================================
@router.post("/auth/logout")
async def logout_endpoint(
    response: Response,
    refresh_token: str | None = Cookie(None),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[None]:
    """用户退出
    撤销当前 Cookie 对应的 Refresh Token 并清除 Cookie；接口幂等。
    """
    request_id = str(uuid.uuid4())

    await logout(db, None, refresh_token)

    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )

    return APIResponse[None](
        code=0,
        message="退出成功",
        data=None,
        request_id=request_id,
    )


# ============================================================
# POST /api/v1/auth/refresh
# ============================================================
@router.post("/auth/refresh")
async def refresh_endpoint(
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token: str | None = Cookie(None),
) -> APIResponse[dict[str, object]]:
    """刷新 Token

    只从 HttpOnly Cookie 读取并轮换 Refresh Token；JSON 仅返回新的 Access Token。
    """
    request_id = str(uuid.uuid4())

    token = refresh_token

    if not token:
        raise UnauthorizedException(
            message="缺少 Refresh Token", request_id=request_id
        )

    try:
        result = await refresh_access_token(db, token)
    except AppException as e:
        e.request_id = request_id
        raise e

    # 更新 Cookie 中的 Refresh Token
    response.set_cookie(
        key="refresh_token",
        value=result.refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/api/v1/auth",
        max_age=_refresh_cookie_max_age(),
    )

    return APIResponse[dict[str, object]](
        code=0,
        message="刷新成功",
        data={
            "access_token": result.access_token,
            "token_type": result.token_type,
            "user": result.user.model_dump(),
        },
        request_id=request_id,
    )


# ============================================================
# GET /api/v1/me
# ============================================================
@router.get("/me")
async def me_endpoint(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict[str, object]]:
    """获取当前用户信息（方案第4.4节）

    返回 id、username、display_name、roles、permissions、knowledge_base_access
    """
    request_id = str(uuid.uuid4())

    me_data = await get_me(db, user.id)

    return APIResponse[dict[str, object]](
        code=0,
        message="success",
        data=me_data.model_dump(),
        request_id=request_id,
    )
