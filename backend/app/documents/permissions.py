"""Permission helpers for document module."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ForbiddenException
from app.common.models import User
from app.common.organization import can_manage_department, is_super_admin
from app.knowledge.models import KnowledgeBase


def user_permission_codes(user: User) -> set[str]:
    codes: set[str] = set()
    for role in user.roles:
        if role.status != "active":
            continue
        for perm in role.permissions:
            codes.add(perm.code)
    return codes


def require_any_permission(user: User, *codes: str) -> None:
    owned = user_permission_codes(user)
    if not any(code in owned for code in codes):
        raise ForbiddenException(message=f"需要权限: {' 或 '.join(codes)}")


async def user_can_access_kb(db: AsyncSession, user: User, kb_id: str) -> bool:
    kb = await db.get(KnowledgeBase, kb_id)
    if kb is None:
        return False
    if kb.kind == "personal":
        return kb.owner_user_id == user.id
    return is_super_admin(user) or kb.department_id == user.department_id


async def user_can_manage_kb(db: AsyncSession, user: User, kb_id: str) -> bool:
    kb = await db.get(KnowledgeBase, kb_id)
    if kb is None:
        return False
    if kb.kind == "personal":
        return kb.owner_user_id == user.id
    return await can_manage_department(db, user, kb.department_id)
