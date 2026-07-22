"""部门管理服务。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import cast

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictException, NotFoundException, ValidationException
from app.common.models import RefreshToken, Role, User
from app.common.organization import is_super_admin
from app.common.schemas import ErrorCode
from app.common.seed import KNOWLEDGE_EDITOR_ROLE_NAME
from app.departments.models import Department
from app.departments.schemas import DepartmentCreate, DepartmentResponse, DepartmentUpdate
from app.knowledge.models import KnowledgeBase


async def _get_user(db: AsyncSession, user_id: str) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundException(message="部门管理员账号不存在")
    if user.status != "active":
        raise ValidationException(message="部门管理员账号必须处于启用状态")
    return user


async def _ensure_name_available(
    db: AsyncSession, name: str, *, exclude_id: str | None = None
) -> None:
    query = select(Department.id).where(
        func.lower(func.btrim(Department.name)) == name.lower()
    )
    if exclude_id is not None:
        query = query.where(Department.id != exclude_id)
    if (await db.execute(query.limit(1))).scalar_one_or_none() is not None:
        raise ConflictException(
            code=ErrorCode.DEPARTMENT_ALREADY_EXISTS,
            message="部门名称已存在",
        )


async def _assign_manager(
    db: AsyncSession, department: Department, user: User
) -> None:
    other = (
        await db.execute(
            select(Department.id).where(
                Department.admin_user_id == user.id,
                Department.id != department.id,
            )
        )
    ).scalar_one_or_none()
    if other is not None:
        raise ConflictException(
            code=ErrorCode.DEPARTMENT_ADMIN_CONFLICT,
            message="该用户已经是其他部门的管理员",
        )

    role = (
        await db.execute(select(Role).where(Role.name == KNOWLEDGE_EDITOR_ROLE_NAME))
    ).scalar_one_or_none()
    changed = department.admin_user_id != user.id or user.department_id != department.id
    department.admin_user_id = user.id
    user.department_id = department.id
    if role is not None and not is_super_admin(user) and (
        len(user.roles) != 1 or user.roles[0].id != role.id
    ):
        user.roles = [role]
        changed = True
    if changed:
        user.session_version += 1
        await db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(timezone.utc))
        )


async def list_departments(db: AsyncSession) -> list[DepartmentResponse]:
    departments = cast(
        list[Department],
        (await db.execute(select(Department).order_by(Department.name))).scalars().all(),
    )
    if not departments:
        return []
    ids = [item.id for item in departments]
    user_counts = {
        row[0]: int(row[1])
        for row in (
            await db.execute(
                select(User.department_id, func.count(User.id))
                .where(User.department_id.in_(ids))
                .group_by(User.department_id)
            )
        ).all()
    }
    kb_counts = {
        row[0]: int(row[1])
        for row in (
            await db.execute(
                select(KnowledgeBase.department_id, func.count(KnowledgeBase.id))
                .where(KnowledgeBase.department_id.in_(ids))
                .group_by(KnowledgeBase.department_id)
            )
        ).all()
    }
    admin_ids = [item.admin_user_id for item in departments if item.admin_user_id]
    admins = (
        {
            item.id: item
            for item in cast(
                list[User],
                (
                    await db.execute(select(User).where(User.id.in_(admin_ids)))
                ).scalars().all(),
            )
        }
        if admin_ids
        else {}
    )
    return [
        DepartmentResponse(
            id=item.id,
            name=item.name,
            description=item.description,
            admin_user_id=item.admin_user_id,
            admin_username=admins[item.admin_user_id].username
            if item.admin_user_id is not None and item.admin_user_id in admins
            else None,
            admin_display_name=admins[item.admin_user_id].display_name
            if item.admin_user_id is not None and item.admin_user_id in admins
            else None,
            user_count=user_counts.get(item.id, 0),
            knowledge_base_count=kb_counts.get(item.id, 0),
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in departments
    ]


async def create_department(
    db: AsyncSession, payload: DepartmentCreate
) -> DepartmentResponse:
    name = " ".join(payload.name.strip().split())
    await _ensure_name_available(db, name)
    manager = await _get_user(db, payload.admin_user_id)
    department = Department(
        name=name,
        description=payload.description.strip() if payload.description else None,
    )
    db.add(department)
    await db.flush()
    await _assign_manager(db, department, manager)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictException(
            code=ErrorCode.DEPARTMENT_ALREADY_EXISTS,
            message="部门名称已存在",
        ) from exc
    return next(item for item in await list_departments(db) if item.id == department.id)


async def update_department(
    db: AsyncSession, department_id: str, payload: DepartmentUpdate
) -> DepartmentResponse:
    department = await db.get(Department, department_id)
    if department is None:
        raise NotFoundException(message="部门不存在")
    if payload.name is not None:
        name = " ".join(payload.name.strip().split())
        await _ensure_name_available(db, name, exclude_id=department.id)
        department.name = name
    if "description" in payload.model_fields_set:
        department.description = payload.description.strip() if payload.description else None
    if payload.admin_user_id is not None:
        await _assign_manager(db, department, await _get_user(db, payload.admin_user_id))
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictException(
            code=ErrorCode.DEPARTMENT_ALREADY_EXISTS,
            message="部门名称已存在",
        ) from exc
    return next(item for item in await list_departments(db) if item.id == department.id)
