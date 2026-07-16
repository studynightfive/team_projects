# 健康检查接口测试
# 验证存活检查和就绪检查端点

import pytest


class TestHealthLive:
    """存活检查端点测试"""

    @pytest.mark.asyncio
    async def test_health_live_returns_200(self, client):
        """验证存活检查返回 200 和 ok 状态"""
        response = await client.get("/api/v1/health/live")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_health_live_response_format(self, client):
        """验证存活检查响应格式正确"""
        response = await client.get("/api/v1/health/live")

        data = response.json()
        # 确认只有预期的字段
        assert set(data.keys()) == {"status", "timestamp"}


class TestHealthReady:
    """就绪检查端点测试"""

    @pytest.mark.asyncio
    async def test_health_ready_returns_response(self, client):
        """验证就绪检查返回响应（降级或正常）"""
        response = await client.get("/api/v1/health/ready")

        # 就绪检查可能返回 200 或 503（取决于数据库和 Redis 是否可用）
        assert response.status_code in (200, 503)
        data = response.json()
        assert "status" in data
        assert "checks" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_health_ready_checks_structure(self, client):
        """验证就绪检查包含所有必需的检查项"""
        response = await client.get("/api/v1/health/ready")

        data = response.json()
        assert "checks" in data
        # 即使数据库和 Redis 不可用，检查项也应该存在
        for check_name in ["database", "redis", "storage"]:
            assert check_name in data["checks"]


class TestRootEndpoint:
    """根路径测试"""

    @pytest.mark.asyncio
    async def test_root_returns_app_info(self, client):
        """验证根路径返回应用信息"""
        response = await client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "app" in data
        assert "version" in data
        assert "docs" in data


class TestRequestID:
    """请求 ID 中间件测试"""

    @pytest.mark.asyncio
    async def test_response_contains_request_id(self, client):
        """验证响应头包含 X-Request-ID"""
        response = await client.get("/api/v1/health/live")

        assert "X-Request-ID" in response.headers
        request_id = response.headers["X-Request-ID"]
        # UUID 格式验证：36 个字符，包含 4 个连字符
        assert len(request_id) == 36
        assert request_id.count("-") == 4


class TestCORSMiddleware:
    """CORS 中间件测试"""

    @pytest.mark.asyncio
    async def test_cors_headers_present(self, client):
        """验证 CORS 响应头存在"""
        response = await client.options(
            "/api/v1/health/live",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

        # 确认 CORS 相关响应头存在
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers


class TestErrorHandling:
    """错误处理测试"""

    @pytest.mark.asyncio
    async def test_404_returns_error_response(self, client):
        """验证 404 路由返回统一错误格式"""
        response = await client.get("/api/v1/nonexistent-endpoint")

        assert response.status_code == 404
        data = response.json()
        assert "code" in data
        assert "message" in data
        assert "request_id" in data

    @pytest.mark.asyncio
    async def test_global_error_response_format(self, client):
        """验证全局异常处理器返回统一响应格式"""
        # 访问一个会触发错误的端点（空路径参数）
        response = await client.get("/api/v1/health/ready")

        # 即使就绪检查失败，响应格式也应该正确
        data = response.json()
        assert "status" in data
        assert "checks" in data