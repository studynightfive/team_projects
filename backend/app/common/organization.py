"""部门数据边界的统一判定。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.models import User
from app.departments.models import Department

SUPER_ADMIN_ROLE_NAME = "超级管理员"


def is_super_admin(user: User) -> bool:
    return any(
        role.status == "active" and role.name == SUPER_ADMIN_ROLE_NAME
        for role in user.roles
    )


async def is_department_admin(db: AsyncSession, user: User) -> bool:
    if user.department_id is None:
        return False
    admin_user_id = (
        await db.execute(
            select(Department.admin_user_id).where(
                Department.id == user.department_id
            )
        )
    ).scalar_one_or_none()
    return admin_user_id == user.id


async def can_manage_department(
    db: AsyncSession, user: User, department_id: str
) -> bool:
    if is_super_admin(user):
        return True
    return user.department_id == department_id and await is_department_admin(db, user)
