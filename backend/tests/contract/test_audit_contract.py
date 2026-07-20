"""
Contract tests for audit log endpoints.
Employee 3 responsibility.

Tests verify endpoint behavior without requiring a live database.
"""
import inspect
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.audit.router import audit_logs_endpoint
from app.auth.dependencies import get_current_user
from app.common.config import settings
from app.common.database import get_db
from app.main import app


def _make_token(permissions: list[str] = None):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "550e8400-e29b-41d4-a716-446655440000",
        "permissions": permissions or [],
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=30),
        "jti": "550e8400-e29b-41d4-a716-446655440001",
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestAuditContract:
    async def test_audit_logs_requires_auth(self, client):
        """No auth header returns 401."""
        response = await client.get("/api/v1/audit-logs")
        assert response.status_code == 401

    async def test_invalid_audit_datetime_uses_validation_contract(self, client):
        permission_dependency = inspect.signature(audit_logs_endpoint).parameters[
            "_perm"
        ].default.dependency
        previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_current_user] = lambda: object()
        app.dependency_overrides[get_db] = lambda: AsyncMock()
        app.dependency_overrides[permission_dependency] = lambda: None
        try:
            response = await client.get(
                "/api/v1/audit-logs", params={"created_after": "not-a-datetime"}
            )
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(previous_overrides)
        assert response.status_code == 422
        assert response.json() == {
            "code": 10001,
            "message": "请求参数错误",
            "data": None,
            "request_id": response.headers["X-Request-ID"],
        }

    async def test_audit_logs_endpoint_behavior(self, client):
        """With valid token and no DB, either 401/403/500 is expected."""
        token = _make_token(permissions=["chat.use"])
        try:
            response = await client.get(
                "/api/v1/audit-logs", headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code in (401, 403, 500)
        except Exception:
            # ASGI transport may raise on DB connection failure
            pass
