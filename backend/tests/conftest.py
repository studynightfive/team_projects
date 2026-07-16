# 测试配置和共享 Fixture
# 为所有测试模块提供统一的测试客户端、认证头和测试数据

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    """
    异步 HTTP 测试客户端
    使用 ASGI transport 直接调用 FastAPI 应用，无需启动真实服务器
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def admin_headers():
    """
    完整管理员认证头
    用于需要全部管理权限的测试场景
    """
    # TODO: 当认证模块就位后，生成真实的 JWT Token
    return {"Authorization": "Bearer admin-test-token"}


@pytest.fixture
def user_headers():
    """
    普通用户认证头
    用于需要普通用户权限的测试场景
    """
    return {"Authorization": "Bearer user-test-token"}


@pytest.fixture
def partial_admin_headers():
    """
    部分权限管理员认证头
    用于测试部分管理员权限边界
    """
    return {"Authorization": "Bearer partial-admin-test-token"}
