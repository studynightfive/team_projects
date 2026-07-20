# 测试配置和共享 Fixture
# 为所有测试模块提供统一的测试客户端、认证头和测试数据

import uuid
from datetime import datetime, timezone

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.common.config import settings
from app.common.database import engine


def _make_token(user_id: str = None, permissions: list[str] = None) -> str:
    """Helper: create a valid JWT access token for testing."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id or str(uuid.uuid4()),
        "permissions": permissions or [],
        "type": "access",
        "iat": now,
        "exp": now + (datetime.now(timezone.utc) - now) + 1800,
        "jti": str(uuid.uuid4()),
    }
    # Use explicit timedelta
    import datetime as dt
    payload["exp"] = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=30)
    payload["iat"] = dt.datetime.now(dt.timezone.utc)
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


@pytest.fixture
async def client():
    """Async HTTP test client using ASGI transport (no real server)."""
    transport = ASGITransport(app=__import__("app.main").main.app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        # ASGITransport 不触发 lifespan，测试必须显式释放共享连接池。
        await engine.dispose()


@pytest.fixture
def admin_token() -> str:
    """JWT token with full admin permissions."""
    return _make_token(permissions=[
        "admin.dashboard.view",
        "admin.user.view",
        "admin.user.create",
        "admin.user.edit",
        "admin.role.view",
        "admin.role.create",
        "admin.role.edit",
        "admin.role.delete",
        "admin.audit.view",
    ])


@pytest.fixture
def user_token() -> str:
    """JWT token with normal user permissions."""
    return _make_token(permissions=["chat.use", "retrieval.search", "document.view"])


@pytest.fixture
def viewer_admin_token() -> str:
    """JWT token with view-only admin permissions."""
    return _make_token(permissions=["admin.user.view", "admin.role.view"])


@pytest.fixture
def partial_admin_token() -> str:
    """JWT token with partial admin permissions."""
    return _make_token(permissions=["admin.user.view", "admin.role.view", "admin.role.edit"])


@pytest.fixture
def admin_headers():
    """Full admin auth headers (legacy, uses test token string)."""
    return {"Authorization": "Bearer admin-test-token"}


@pytest.fixture
def user_headers():
    """Normal user auth headers (legacy, uses test token string)."""
    return {"Authorization": "Bearer user-test-token"}


@pytest.fixture
def partial_admin_headers():
    """Partial admin auth headers (legacy, uses test token string)."""
    return {"Authorization": "Bearer partial-admin-test-token"}
