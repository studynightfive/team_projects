# 契约测试共享 Fixture
# 为所有契约测试模块提供统一的测试客户端和认证头

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
    拥有全部管理权限（admin.*）
    用于需要全部管理权限的测试场景
    """
    return {"Authorization": "Bearer admin-test-token"}


@pytest.fixture
def user_headers():
    """
    普通用户认证头
    仅拥有用户工作区权限，不包含 admin.*
    用于测试普通用户权限边界
    """
    return {"Authorization": "Bearer user-test-token"}


@pytest.fixture
def partial_admin_headers():
    """
    部分权限管理员认证头
    仅拥有部分管理权限（如仅 admin.user.view）
    用于测试部分管理员权限边界
    """
    return {"Authorization": "Bearer partial-admin-test-token"}


@pytest.fixture
def viewer_admin_headers():
    """
    仅查看权限管理员认证头
    仅拥有查看类管理权限，无编辑/删除权限
    """
    return {"Authorization": "Bearer viewer-admin-test-token"}


@pytest.fixture
def disabled_user_headers():
    """
    已禁用用户认证头
    用于测试用户禁用后会话失效
    """
    return {"Authorization": "Bearer disabled-user-test-token"}


@pytest.fixture
def no_auth_headers():
    """
    无认证头
    用于测试未登录访问
    """
    return {}
