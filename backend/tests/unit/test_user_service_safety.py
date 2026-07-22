"""用户写入竞争与管理契约回归测试。"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.common.exceptions import ConflictException, ValidationException
from app.common.models import Role, User
from app.common.schemas import ErrorCode
from app.users.schemas import CreateUserRequest, UpdateUserRequest
from app.users.service import (
    _ensure_assignable_role,
    _ensure_role_change_allowed,
    create_user,
)


def test_update_user_rejects_display_name() -> None:
    with pytest.raises(ValidationError):
        UpdateUserRequest.model_validate({"display_name": "不应由管理员修改"})


def test_user_role_assignment_requires_exactly_one_role() -> None:
    with pytest.raises(ValidationError):
        CreateUserRequest(
            username="multi-role",
            display_name="多角色用户",
            password="safe-password",
            role_ids=["role-1", "role-2"],
        )


def test_super_admin_role_is_not_assignable() -> None:
    role = Role(id="super-role", name="超级管理员", status="active")
    with pytest.raises(ValidationException, match="不能分配超级管理员"):
        _ensure_assignable_role([role])


def test_super_admin_role_cannot_be_changed_by_user_management() -> None:
    role = Role(id="super-role", name="超级管理员", status="active")
    user = User(id="admin-user", username="admin", display_name="管理员")
    user.roles = [role]

    with pytest.raises(ValidationException, match="不能通过用户管理修改"):
        _ensure_role_change_allowed(user)


@pytest.mark.asyncio
async def test_create_user_maps_unique_race_to_conflict() -> None:
    db = AsyncMock()
    db.add = Mock()
    initial_lookup = Mock()
    initial_lookup.scalar_one_or_none.return_value = None
    role = Role(id="user-role", name="普通用户", status="active")
    role_lookup = Mock()
    role_lookup.scalars.return_value.all.return_value = [role]
    duplicate_lookup = Mock()
    duplicate_lookup.scalar_one_or_none.return_value = "existing-user-id"
    db.execute.side_effect = [initial_lookup, role_lookup, duplicate_lookup]
    db.commit.side_effect = IntegrityError("insert", {}, Exception("duplicate"))

    with (
        patch(
            "app.knowledge.service.ensure_personal_knowledge_base",
            new=AsyncMock(),
        ),
        pytest.raises(ConflictException) as exc_info,
    ):
        await create_user(
            db,
            CreateUserRequest(
                username="same-user",
                display_name="并发用户",
                password="safe-password",
                role_ids=[role.id],
            ),
        )

    assert exc_info.value.code == ErrorCode.USER_ALREADY_EXISTS
    assert exc_info.value.status_code == 409
    db.rollback.assert_awaited_once()
