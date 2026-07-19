# 认证路由
# 员工3 负责
# 对应 OpenAPI：POST /auth/login、POST /auth/logout、POST /auth/refresh、GET /me

import uuid

import structlog
from fastapi import APIRouter, Cookie, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.schemas import LoginRequest, RegisterRequest, UsernameAvailability
from app.auth.service import get_me, login, logout, refresh_access_token
from app.common.database import get_db
from app.common.exceptions import AppException
from app.common.models import Role, User
from app.common.schemas import APIResponse
from app.users.schemas import CreateUserRequest
from app.users.service import create_user

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["auth"])


@router.get("/auth/check-username")
async def check_username_endpoint(
    username: str,
    db: AsyncSession = Depends(get_db),
):
    """检查账号 ID 是否可注册。"""
    normalized = username.strip()
    existing = None
    if normalized != "":
        result = await db.execute(select(User.id).where(User.username == normalized))
        existing = result.scalar_one_or_none()
    return APIResponse(
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
):
    """公开注册普通用户账号，创建后进入用户管理列表。"""
    request_id = str(uuid.uuid4())
    role_result = await db.execute(select(Role).where(Role.name == "普通用户"))
    user_role = role_result.scalar_one_or_none()
    role_ids = [user_role.id] if user_role is not None else []

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

    return APIResponse(
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
):
    """用户登录（方案第5.2节）

    返回 Access Token 和 Refresh Token。
    前端应将 Refresh Token 存储于 HttpOnly Cookie，
    不在 localStorage、URL 或日志中保存 Token。
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
        secure=False,  # 生产通过 Nginx TLS 保证
        samesite="lax",
        path="/api/v1/auth",
        max_age=7 * 24 * 3600,
    )

    return APIResponse(
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
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """用户退出
    撤销所有 Refresh Token 并清除 Cookie
    """
    request_id = str(uuid.uuid4())

    await logout(db, user.id)

    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth",
    )

    return APIResponse(
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
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token: str | None = Cookie(None),
):
    """刷新 Token

    从 Cookie 读取 Refresh Token，验证后返回新的 Token 对。
    也支持从请求体 JSON 中读取 refresh_token 字段（备选）。
    """
    request_id = str(uuid.uuid4())

    # 优先从 Cookie 读取
    token = refresh_token

    # 备选：从请求体 JSON 读取
    if not token:
        try:
            body = await request.json()
            token = body.get("refresh_token")
        except Exception:
            pass

    if not token:
        from app.common.exceptions import UnauthorizedException

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
        secure=False,
        samesite="lax",
        path="/api/v1/auth",
        max_age=7 * 24 * 3600,
    )

    return APIResponse(
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
):
    """获取当前用户信息（方案第4.4节）

    返回 id、username、display_name、roles、permissions、knowledge_base_access
    """
    request_id = str(uuid.uuid4())

    me_data = await get_me(db, user.id)

    return APIResponse(
        code=0,
        message="success",
        data=me_data.model_dump(),
        request_id=request_id,
    )
