# 角色服务层
# 员工3 负责
# 角色的 CRUD 操作和权限分配

from typing import cast

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import (
    ConflictException,
    NotFoundException,
    ValidationException,
)
from app.common.models import Permission, Role
from app.common.schemas import ErrorCode
from app.users.role_schemas import (
    CreateRoleRequest,
    PermissionResponse,
    RoleListItem,
    RoleResponse,
    SetRolePermissionsRequest,
    UpdateRoleRequest,
)

logger = structlog.get_logger()


# ============================================================
# 角色 CRUD
# ============================================================
async def list_roles(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[RoleListItem], int]:
    """分页查询角色列表"""
    query = select(Role)

    # 计算总数
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar() or 0

    # 分页
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(Role.created_at.desc()).offset(offset).limit(page_size)
    )
    roles = cast(list[Role], result.scalars().all())

    items = [
        RoleListItem(
            id=r.id,
            name=r.name,
            description=r.description,
            status=r.status,
            permissions_count=len(r.permissions),
            created_at=r.created_at,
        )
        for r in roles
    ]

    return items, total


async def list_all_roles(db: AsyncSession) -> list[RoleListItem]:
    """获取所有活跃角色（不分页，用于下拉选择）"""
    result = await db.execute(
        select(Role).where(Role.status == "active").order_by(Role.name)
    )
    roles = cast(list[Role], result.scalars().all())

    return [
        RoleListItem(
            id=r.id,
            name=r.name,
            description=r.description,
            status=r.status,
            permissions_count=len(r.permissions),
            created_at=r.created_at,
        )
        for r in roles
    ]


async def create_role(db: AsyncSession, data: CreateRoleRequest) -> RoleResponse:
    """创建角色"""
    # 检查名称唯一性
    result = await db.execute(
        select(Role).where(Role.name == data.name)
    )
    if result.scalar_one_or_none():
        raise ConflictException(
            code=ErrorCode.ROLE_ALREADY_EXISTS,
            message="角色名已存在",
        )

    role = Role(
        name=data.name,
        description=data.description,
        status="active",
    )

    # 分配权限
    if data.permission_ids:
        result = await db.execute(
            select(Permission).where(Permission.id.in_(data.permission_ids))
        )
        permissions = cast(list[Permission], result.scalars().all())
        if len(permissions) != len(data.permission_ids):
            raise NotFoundException(
                code=ErrorCode.PERMISSION_NOT_FOUND,
                message="部分权限不存在",
            )
        role.permissions = list(permissions)

    db.add(role)
    await db.commit()
    await db.refresh(role)

    return _to_role_response(role)


async def get_role(db: AsyncSession, role_id: str) -> RoleResponse:
    """获取角色详情"""
    role = await _get_role_or_404(db, role_id)
    return _to_role_response(role)


async def update_role(
    db: AsyncSession, role_id: str, data: UpdateRoleRequest
) -> RoleResponse:
    """更新角色"""
    role = await _get_role_or_404(db, role_id)

    if data.name is not None:
        # 检查名称唯一性
        result = await db.execute(
            select(Role).where(Role.name == data.name, Role.id != role_id)
        )
        if result.scalar_one_or_none():
            raise ConflictException(
                code=ErrorCode.ROLE_ALREADY_EXISTS,
                message="角色名已存在",
            )
        role.name = data.name
    if data.description is not None:
        role.description = data.description
    if data.status is not None:
        if data.status not in ("active", "disabled"):
            raise ValidationException(message="角色状态必须为 active 或 disabled")
        role.status = data.status

    await db.commit()
    await db.refresh(role)
    return _to_role_response(role)


async def delete_role(db: AsyncSession, role_id: str) -> None:
    """删除角色"""
    role = await _get_role_or_404(db, role_id)
    await db.delete(role)
    await db.commit()


async def set_role_permissions(
    db: AsyncSession, role_id: str, data: SetRolePermissionsRequest
) -> RoleResponse:
    """设置角色权限"""
    role = await _get_role_or_404(db, role_id)

    if data.permission_ids:
        result = await db.execute(
            select(Permission).where(Permission.id.in_(data.permission_ids))
        )
        permissions = cast(list[Permission], result.scalars().all())
        if len(permissions) != len(data.permission_ids):
            raise NotFoundException(
                code=ErrorCode.PERMISSION_NOT_FOUND,
                message="部分权限不存在",
            )
        role.permissions = list(permissions)
    else:
        role.permissions = []

    await db.commit()
    await db.refresh(role)
    return _to_role_response(role)


# ============================================================
# 权限查询
# ============================================================
async def list_permissions(
    db: AsyncSession, module: str | None = None
) -> list[PermissionResponse]:
    """获取权限码列表（用于管理界面配置角色）"""
    query = select(Permission)
    if module:
        query = query.where(Permission.module == module)
    query = query.order_by(Permission.module, Permission.action)

    result = await db.execute(query)
    permissions = cast(list[Permission], result.scalars().all())

    return [
        PermissionResponse(
            id=p.id,
            code=p.code,
            name=p.name,
            module=p.module,
            action=p.action,
        )
        for p in permissions
    ]


# ============================================================
# 辅助函数
# ============================================================
async def _get_role_or_404(db: AsyncSession, role_id: str) -> Role:
    """获取角色或抛出 404"""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if role is None:
        raise NotFoundException(
            code=ErrorCode.ROLE_NOT_FOUND,
            message="角色不存在",
        )
    return role


def _to_role_response(role: Role) -> RoleResponse:
    """将 ORM 模型转为响应模型"""
    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        status=role.status,
        permissions=[
            PermissionResponse(
                id=p.id,
                code=p.code,
                name=p.name,
                module=p.module,
                action=p.action,
            )
            for p in role.permissions
        ],
        created_at=role.created_at,
        updated_at=role.updated_at,
    )
