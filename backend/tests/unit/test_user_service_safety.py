"""用户写入竞争与管理契约回归测试。"""

from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.common.exceptions import ConflictException
from app.common.schemas import ErrorCode
from app.users.schemas import CreateUserRequest, UpdateUserRequest
from app.users.service import create_user


def test_update_user_rejects_display_name() -> None:
    with pytest.raises(ValidationError):
        UpdateUserRequest.model_validate({"display_name": "不应由管理员修改"})


@pytest.mark.asyncio
async def test_create_user_maps_unique_race_to_conflict() -> None:
    db = AsyncMock()
    db.add = Mock()
    initial_lookup = Mock()
    initial_lookup.scalar_one_or_none.return_value = None
    duplicate_lookup = Mock()
    duplicate_lookup.scalar_one_or_none.return_value = "existing-user-id"
    db.execute.side_effect = [initial_lookup, duplicate_lookup]
    db.commit.side_effect = IntegrityError("insert", {}, Exception("duplicate"))

    with pytest.raises(ConflictException) as exc_info:
        await create_user(
            db,
            CreateUserRequest(
                username="same-user",
                display_name="并发用户",
                password="safe-password",
            ),
        )

    assert exc_info.value.code == ErrorCode.USER_ALREADY_EXISTS
    assert exc_info.value.status_code == 409
    db.rollback.assert_awaited_once()
