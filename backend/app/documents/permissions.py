"""Permission helpers for document module."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ForbiddenException
from app.common.models import KnowledgeBasePermission, User


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
    perms = user_permission_codes(user)
    if "admin.document.view" in perms or "admin.document.upload" in perms:
        return True
    role_ids = [role.id for role in user.roles if role.status == "active"]
    if role_ids:
        result = await db.execute(
            select(KnowledgeBasePermission).where(
                KnowledgeBasePermission.subject_type == "role",
                KnowledgeBasePermission.subject_id.in_(role_ids),
                KnowledgeBasePermission.kb_id == kb_id,
            )
        )
        if result.scalar_one_or_none() is not None:
            return True
    result = await db.execute(
        select(KnowledgeBasePermission).where(
            KnowledgeBasePermission.subject_type == "user",
            KnowledgeBasePermission.subject_id == user.id,
            KnowledgeBasePermission.kb_id == kb_id,
        )
    )
    return result.scalar_one_or_none() is not None
