# 用户服务层
# 员工3 负责
# 用户的 CRUD 操作和密码重置

import structlog
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_password
from app.common.exceptions import (
    ConflictException,
    NotFoundException,
    ValidationException,
)
from app.common.models import Role, User, user_roles
from app.common.schemas import ErrorCode
from app.users.schemas import (
    CreateUserRequest,
    UpdateUserRequest,
    UserListItem,
    UserResponse,
)

logger = structlog.get_logger()


# ============================================================
# 用户 CRUD
# ============================================================
async def list_users(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    status: str | None = None,
) -> tuple[list[UserListItem], int]:
    """分页查询用户列表"""
    query = select(User)

    if search:
        query = query.where(
            or_(
                User.username.ilike(f"%{search}%"),
                User.display_name.ilike(f"%{search}%"),
            )
        )
    if status:
        query = query.where(User.status == status)

    # 计算总数
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar() or 0

    # 分页
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(User.created_at.desc()).offset(offset).limit(page_size)
    )
    users = result.scalars().all()

    items = [
        UserListItem(
            id=u.id,
            username=u.username,
            display_name=u.display_name,
            status=u.status,
            roles=[
                {"id": r.id, "name": r.name}
                for r in u.roles
            ],
            last_login_at=u.last_login_at,
            created_at=u.created_at,
        )
        for u in users
    ]

    return items, total


async def create_user(db: AsyncSession, data: CreateUserRequest) -> UserResponse:
    """创建用户"""
    # 检查用户名唯一性
    result = await db.execute(
        select(User).where(User.username == data.username)
    )
    if result.scalar_one_or_none():
        raise ConflictException(
            code=ErrorCode.USER_ALREADY_EXISTS,
            message="用户名已存在",
        )

    user = User(
        username=data.username,
        display_name=data.display_name,
        password_hash=hash_password(data.password),
        status="active",
    )

    # 分配角色
    if data.role_ids:
        result = await db.execute(
            select(Role).where(Role.id.in_(data.role_ids))
        )
        roles = result.scalars().all()
        if len(roles) != len(data.role_ids):
            raise NotFoundException(
                code=ErrorCode.ROLE_NOT_FOUND,
                message="部分角色不存在",
            )
        user.roles = list(roles)

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return _to_user_response(user)


async def get_user(db: AsyncSession, user_id: str) -> UserResponse:
    """获取用户详情"""
    user = await _get_user_or_404(db, user_id)
    return _to_user_response(user)


async def update_user(
    db: AsyncSession, user_id: str, data: UpdateUserRequest
) -> UserResponse:
    """更新用户"""
    user = await _get_user_or_404(db, user_id)

    if data.display_name is not None:
        user.display_name = data.display_name
    if data.status is not None:
        if data.status not in ("active", "disabled"):
            raise ValidationException(message="用户状态必须为 active 或 disabled")
        user.status = data.status
    if data.role_ids is not None:
        result = await db.execute(
            select(Role).where(Role.id.in_(data.role_ids))
        )
        roles = result.scalars().all()
        if len(roles) != len(data.role_ids):
            raise NotFoundException(
                code=ErrorCode.ROLE_NOT_FOUND,
                message="部分角色不存在",
            )
        user.roles = list(roles)

    await db.commit()
    await db.refresh(user)
    return _to_user_response(user)


async def reset_user_password(
    db: AsyncSession, user_id: str, new_password: str
) -> None:
    """重置用户密码"""
    user = await _get_user_or_404(db, user_id)

    if len(new_password) < 8:
        raise ValidationException(message="密码长度至少 8 位")

    user.password_hash = hash_password(new_password)
    await db.commit()


# ============================================================
# 辅助函数
# ============================================================
async def _get_user_or_404(db: AsyncSession, user_id: str) -> User:
    """获取用户或抛出 404"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFoundException(
            code=ErrorCode.USER_NOT_FOUND,
            message="用户不存在",
        )
    return user


def _to_user_response(user: User) -> UserResponse:
    """将 ORM 模型转为响应模型"""
    return UserResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        status=user.status,
        roles=[
            {"id": r.id, "name": r.name}
            for r in user.roles
        ],
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
