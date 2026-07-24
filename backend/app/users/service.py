# 用户服务层
# 员工3 负责
# 用户的 CRUD 操作和密码重置

from datetime import datetime, timezone
from typing import cast

import structlog
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_password
from app.common.exceptions import (
    ConflictException,
    NotFoundException,
    ValidationException,
)
from app.common.models import RefreshToken, Role, User
from app.common.organization import SUPER_ADMIN_ROLE_NAME, is_super_admin
from app.common.schemas import ErrorCode
from app.departments.models import Department
from app.departments.schemas import DepartmentBrief
from app.knowledge.models import KnowledgeBase
from app.users.schemas import (
    CreateUserRequest,
    RoleBrief,
    UpdateUserRequest,
    UserListItem,
    UserResponse,
)

logger = structlog.get_logger()


def _ensure_assignable_role(roles: list[Role]) -> None:
    if any(role.name == SUPER_ADMIN_ROLE_NAME for role in roles):
        raise ValidationException(message="用户管理不能分配超级管理员角色")


def _ensure_role_change_allowed(user: User) -> None:
    if is_super_admin(user):
        raise ValidationException(message="超级管理员角色不能通过用户管理修改")


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
    users = cast(list[User], result.scalars().all())
    department_ids = {u.department_id for u in users if u.department_id is not None}
    departments = (
        {
            item.id: item
            for item in cast(
                list[Department],
                (
                    await db.execute(
                        select(Department).where(Department.id.in_(department_ids))
                    )
                ).scalars().all(),
            )
        }
        if department_ids
        else {}
    )

    items = [
        UserListItem(
            id=u.id,
            username=u.username,
            display_name=u.display_name,
            status=u.status,
            roles=[
                RoleBrief(id=r.id, name=r.name)
                for r in u.roles
            ],
            department=_department_brief(
                departments.get(u.department_id) if u.department_id else None
            ),
            last_login_at=u.last_login_at,
            created_at=u.created_at,
        )
        for u in users
    ]

    return items, total


async def create_user(db: AsyncSession, data: CreateUserRequest) -> UserResponse:
    """创建用户"""
    username = data.username.strip()
    display_name = data.display_name.strip()
    if username == "" or display_name == "":
        raise ValidationException(message="账号 ID 和姓名不能为空")

    # 检查用户名唯一性
    result = await db.execute(
        select(User).where(User.username == username)
    )
    if result.scalar_one_or_none():
        raise ConflictException(
            code=ErrorCode.USER_ALREADY_EXISTS,
            message="用户名已存在",
        )

    user = User(
        username=username,
        display_name=display_name,
        password_hash=hash_password(data.password),
        status="active",
    )
    department = None
    if data.department_id is not None:
        department = await db.get(Department, data.department_id)
        if department is None:
            raise NotFoundException(message="部门不存在")
        user.department_id = department.id

    # 分配角色
    if data.role_ids:
        result = await db.execute(
            select(Role).where(Role.id.in_(data.role_ids))
        )
        roles = cast(list[Role], result.scalars().all())
        if len(roles) != len(data.role_ids):
            raise NotFoundException(
                code=ErrorCode.ROLE_NOT_FOUND,
                message="部分角色不存在",
            )
        _ensure_assignable_role(roles)
        user.roles = list(roles)

    db.add(user)
    try:
        await db.flush()
        from app.knowledge.service import ensure_personal_knowledge_base

        await ensure_personal_knowledge_base(db, user)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        duplicate = await db.execute(select(User.id).where(User.username == username))
        if duplicate.scalar_one_or_none() is not None:
            raise ConflictException(
                code=ErrorCode.USER_ALREADY_EXISTS,
                message="用户名已存在",
            ) from exc
        raise
    await db.refresh(user)

    return _to_user_response(user, department)


async def get_user(db: AsyncSession, user_id: str) -> UserResponse:
    """获取用户详情"""
    user = await _get_user_or_404(db, user_id)
    department = await db.get(Department, user.department_id) if user.department_id else None
    return _to_user_response(user, department)


async def update_user(
    db: AsyncSession, user_id: str, data: UpdateUserRequest
) -> UserResponse:
    """更新用户"""
    user = await _get_user_or_404(db, user_id, for_update=True)
    invalidate_sessions = False

    if data.status is not None:
        if data.status not in ("active", "disabled"):
            raise ValidationException(message="用户状态必须为 active 或 disabled")
        if user.status != data.status:
            user.status = data.status
            invalidate_sessions = True
    if data.role_ids is not None:
        _ensure_role_change_allowed(user)
        result = await db.execute(
            select(Role).where(Role.id.in_(data.role_ids))
        )
        roles = cast(list[Role], result.scalars().all())
        if len(roles) != len(data.role_ids):
            raise NotFoundException(
                code=ErrorCode.ROLE_NOT_FOUND,
                message="部分角色不存在",
            )
        _ensure_assignable_role(roles)
        if {role.id for role in user.roles} != {role.id for role in roles}:
            user.roles = list(roles)
            invalidate_sessions = True
    if "department_id" in data.model_fields_set:
        if data.department_id is None:
            raise ValidationException(message="用户必须归属一个部门")
        department = await db.get(Department, data.department_id)
        if department is None:
            raise NotFoundException(message="部门不存在")
        managed_department = (
            await db.execute(
                select(Department.id).where(
                    Department.admin_user_id == user.id,
                    Department.id != department.id,
                )
            )
        ).scalar_one_or_none()
        if managed_department is not None:
            raise ConflictException(
                code=ErrorCode.DEPARTMENT_ADMIN_CONFLICT,
                message="请先为原部门更换管理员，再调整该用户部门",
            )
        if user.department_id != department.id:
            user.department_id = department.id
            invalidate_sessions = True
        await db.execute(
            update(KnowledgeBase)
            .where(
                KnowledgeBase.kind == "personal",
                KnowledgeBase.owner_user_id == user.id,
            )
            .values(department_id=department.id)
        )

    if invalidate_sessions:
        await _invalidate_user_sessions(db, user)

    await db.commit()
    await db.refresh(user)
    department = await db.get(Department, user.department_id) if user.department_id else None
    return _to_user_response(user, department)


async def reset_user_password(
    db: AsyncSession, user_id: str, new_password: str
) -> None:
    """重置用户密码"""
    user = await _get_user_or_404(db, user_id, for_update=True)

    if len(new_password) < 7:
        raise ValidationException(message="密码长度至少 7 位")

    user.password_hash = hash_password(new_password)
    await _invalidate_user_sessions(db, user)
    await db.commit()


# ============================================================
# 辅助函数
# ============================================================
async def _get_user_or_404(
    db: AsyncSession,
    user_id: str,
    *,
    for_update: bool = False,
) -> User:
    """获取用户或抛出 404"""
    query = select(User).where(User.id == user_id)
    if for_update:
        query = query.with_for_update()
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFoundException(
            code=ErrorCode.USER_NOT_FOUND,
            message="用户不存在",
        )
    return user


async def _invalidate_user_sessions(db: AsyncSession, user: User) -> None:
    """递增会话版本并撤销刷新令牌；调用方负责在同一事务提交。"""
    user.session_version += 1
    await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(timezone.utc))
    )


def _department_brief(department: Department | None) -> DepartmentBrief | None:
    if department is None:
        return None
    return DepartmentBrief(id=department.id, name=department.name)


def _to_user_response(
    user: User, department: Department | None = None
) -> UserResponse:
    """将 ORM 模型转为响应模型"""
    return UserResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        status=user.status,
        roles=[RoleBrief(id=r.id, name=r.name) for r in user.roles],
        department=_department_brief(department),
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
