"""安全敏感的用户变更必须立即终止既有会话。"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.auth.dependencies import get_current_user
from app.auth.security import create_access_token, create_refresh_token, hash_password
from app.auth.service import refresh_access_token
from app.common.database import async_session_factory
from app.common.exceptions import TokenInvalidException
from app.common.models import RefreshToken, Role, User
from app.users.schemas import UpdateUserRequest
from app.users.service import reset_user_password, update_user


def _request() -> Request:
    return Request({"type": "http", "method": "GET", "path": "/", "headers": []})


async def _create_user_session(
    db: AsyncSession,
    *,
    roles: list[Role] | None = None,
) -> tuple[User, str, str]:
    user = User(
        id=str(uuid.uuid4()),
        username=f"session-test-{uuid.uuid4()}",
        display_name="会话失效测试用户",
        password_hash=hash_password("old-password"),
        status="active",
    )
    user.roles = roles or []
    db.add(user)
    await db.flush()

    raw_refresh_token, token_hash = create_refresh_token(user.id)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
    )
    await db.commit()

    access_token = create_access_token(
        user.id,
        [],
        session_version=user.session_version,
    )
    return user, access_token, raw_refresh_token


async def _assert_old_session_is_invalid(
    db: AsyncSession,
    *,
    user: User,
    access_token: str,
    refresh_token: str,
) -> None:
    with pytest.raises(TokenInvalidException):
        await get_current_user(
            request=_request(),
            db=db,
            authorization=f"Bearer {access_token}",
        )

    with pytest.raises(TokenInvalidException):
        await refresh_access_token(db, refresh_token)

    current_access_token = create_access_token(
        user.id,
        [],
        session_version=user.session_version,
    )
    current_user = await get_current_user(
        request=_request(),
        db=db,
        authorization=f"Bearer {current_access_token}",
    )
    assert current_user.id == user.id


async def _cleanup(user_id: str, role_ids: list[str] | None = None) -> None:
    async with async_session_factory() as db:
        await db.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
        await db.execute(delete(User).where(User.id == user_id))
        if role_ids:
            await db.execute(delete(Role).where(Role.id.in_(role_ids)))
        await db.commit()


async def test_password_reset_invalidates_access_and_refresh_tokens() -> None:
    async with async_session_factory() as db:
        user, access_token, refresh_token = await _create_user_session(db)
        try:
            await reset_user_password(db, user.id, "new-password")
            await db.refresh(user)

            assert user.session_version == 1
            token_record = (
                await db.execute(
                    select(RefreshToken).where(RefreshToken.user_id == user.id)
                )
            ).scalar_one()
            assert token_record.revoked_at is not None
            await _assert_old_session_is_invalid(
                db,
                user=user,
                access_token=access_token,
                refresh_token=refresh_token,
            )
        finally:
            await db.close()
            await _cleanup(user.id)


async def test_disable_then_reenable_does_not_revive_old_session() -> None:
    async with async_session_factory() as db:
        user, access_token, refresh_token = await _create_user_session(db)
        try:
            await update_user(db, user.id, UpdateUserRequest(status="disabled"))
            await update_user(db, user.id, UpdateUserRequest(status="active"))
            await db.refresh(user)

            assert user.status == "active"
            assert user.session_version == 2
            await _assert_old_session_is_invalid(
                db,
                user=user,
                access_token=access_token,
                refresh_token=refresh_token,
            )
        finally:
            await db.close()
            await _cleanup(user.id)


async def test_role_assignment_change_invalidates_old_session() -> None:
    first_role = Role(
        id=str(uuid.uuid4()),
        name=f"session-role-{uuid.uuid4()}",
        description="变更前角色",
        status="active",
    )
    second_role = Role(
        id=str(uuid.uuid4()),
        name=f"session-role-{uuid.uuid4()}",
        description="变更后角色",
        status="active",
    )
    async with async_session_factory() as db:
        db.add_all([first_role, second_role])
        user, access_token, refresh_token = await _create_user_session(
            db,
            roles=[first_role],
        )
        try:
            await update_user(
                db,
                user.id,
                UpdateUserRequest(role_ids=[second_role.id]),
            )
            await db.refresh(user)

            assert user.session_version == 1
            assert {role.id for role in user.roles} == {second_role.id}
            await _assert_old_session_is_invalid(
                db,
                user=user,
                access_token=access_token,
                refresh_token=refresh_token,
            )
        finally:
            await db.close()
            await _cleanup(user.id, [first_role.id, second_role.id])
