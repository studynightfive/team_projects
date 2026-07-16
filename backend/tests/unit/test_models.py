"""Unit tests for database ORM models."""
import uuid

import pytest

from app.common.models import (
    AuditLog,
    KnowledgeBasePermission,
    Permission,
    RefreshToken,
    Role,
    User,
)


class TestUserModel:
    """Test User ORM model."""

    def test_user_creation(self):
        """User can be created with required fields."""
        user = User(
            id=str(uuid.uuid4()),
            username="testuser",
            display_name="Test User",
            password_hash="$argon2...",
            status="active",
        )
        assert user.username == "testuser"
        assert user.display_name == "Test User"
        assert user.status == "active"
        assert user.id is not None

    def test_user_default_status_active(self):
        """Default user status is 'active'."""
        assert User.status.default.arg == "active"

    def test_user_relationships_exist(self):
        """User has roles and audit_logs relationships."""
        user = User(
            id=str(uuid.uuid4()),
            username="u1",
            display_name="User 1",
            password_hash="...",
            status="active",
        )
        assert isinstance(user.roles, list)
        assert isinstance(user.audit_logs, list)


class TestRoleModel:
    """Test Role ORM model."""

    def test_role_creation(self):
        """Role can be created with required fields."""
        role = Role(
            id=str(uuid.uuid4()),
            name="Admin",
            description="Administrator",
            status="active",
        )
        assert role.name == "Admin"
        assert role.status == "active"
        assert isinstance(role.permissions, list)
        assert isinstance(role.users, list)


class TestPermissionModel:
    """Test Permission ORM model."""

    def test_permission_creation(self):
        """Permission can be created with required fields."""
        perm = Permission(
            id=str(uuid.uuid4()),
            code="admin.user.view",
            name="View Users",
            module="admin",
            action="user.view",
        )
        assert perm.code == "admin.user.view"
        assert perm.module == "admin"
        assert perm.action == "user.view"


class TestKnowledgeBasePermissionModel:
    """Test KnowledgeBasePermission ORM model."""

    def test_kb_permission_creation(self):
        """KnowledgeBasePermission can be created."""
        perm = KnowledgeBasePermission(
            id=str(uuid.uuid4()),
            subject_type="user",
            subject_id=str(uuid.uuid4()),
            kb_id=str(uuid.uuid4()),
            access_level="read",
        )
        assert perm.subject_type == "user"
        assert perm.access_level == "read"


class TestRefreshTokenModel:
    """Test RefreshToken ORM model."""

    def test_refresh_token_creation(self):
        """RefreshToken can be created."""
        uid = str(uuid.uuid4())
        from datetime import datetime, timezone

        token = RefreshToken(
            id=str(uuid.uuid4()),
            user_id=uid,
            token_hash="abc123hash",
            expires_at=datetime.now(timezone.utc),
        )
        assert token.user_id == uid
        assert token.token_hash == "abc123hash"
        assert token.revoked_at is None


class TestAuditLogModel:
    """Test AuditLog ORM model."""

    def test_audit_log_creation(self):
        """AuditLog can be created."""
        log = AuditLog(
            id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            action="user.login",
            resource_type="user",
            resource_id=str(uuid.uuid4()),
            result="success",
        )
        assert log.action == "user.login"
        assert log.result == "success"

    def test_audit_log_default_result_success(self):
        """Default AuditLog result is 'success'."""
        assert AuditLog.result.default.arg == "success"
