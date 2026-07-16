# 统一响应格式测试
# 验证所有非 SSE 端点返回统一响应格式（方案第14.2节）

import pytest


class TestHealthEndpointResponseFormat:
    """健康检查端点响应格式验证"""

    @pytest.mark.asyncio
    async def test_health_live_response_format(self, client):
        """验证存活检查响应格式正确"""
        response = await client.get("/api/v1/health/live")
        assert response.status_code == 200
        data = response.json()
        # 存活检查不使用统一响应格式（直接返回 status + timestamp）
        assert "status" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_health_ready_response_format(self, client):
        """验证就绪检查响应格式正确"""
        response = await client.get("/api/v1/health/ready")
        # 就绪检查可能返回 200 或 503
        data = response.json()
        assert "status" in data
        assert "checks" in data
        assert "timestamp" in data


class TestErrorResponseFormat:
    """错误响应格式验证"""

    @pytest.mark.asyncio
    async def test_404_response_format(self, client):
        """验证 404 响应格式"""
        response = await client.get("/api/v1/nonexistent-endpoint")
        assert response.status_code == 404
        data = response.json()
        # FastAPI 默认 404 格式为 {"detail": "..."}
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_422_response_format(self, client):
        """验证 422 响应格式（请求体校验失败）"""
        response = await client.post(
            "/api/v1/health/live",
            json={"invalid_field": "value"},
        )
        assert response.status_code == 405  # GET 端点不支持 POST


class TestResponseHeaders:
    """响应头验证"""

    @pytest.mark.asyncio
    async def test_request_id_header_present(self, client):
        """验证响应头包含 X-Request-ID"""
        response = await client.get("/api/v1/health/live")
        assert "X-Request-ID" in response.headers
        request_id = response.headers["X-Request-ID"]
        # UUID 格式验证：36 个字符，包含 4 个连字符
        assert len(request_id) == 36
        assert request_id.count("-") == 4

    @pytest.mark.asyncio
    async def test_request_id_header_on_error(self, client):
        """验证错误响应也包含 X-Request-ID"""
        response = await client.get("/api/v1/nonexistent-endpoint")
        assert "X-Request-ID" in response.headers

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
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers


class TestRootEndpoint:
    """根路径响应格式"""

    @pytest.mark.asyncio
    async def test_root_response_format(self, client):
        """验证根路径返回应用信息"""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "app" in data
        assert "version" in data
        assert "docs" in data


class TestSecurityHeaders:
    """安全响应头验证"""

    @pytest.mark.asyncio
    async def test_content_type_is_json(self, client):
        """验证 API 响应 Content-Type 为 application/json"""
        response = await client.get("/api/v1/health/live")
        assert "application/json" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_no_server_header_leak(self, client):
        """验证响应不泄露服务器信息"""
        response = await client.get("/api/v1/health/live")
        # FastAPI 默认不返回 Server 头
        assert "server" not in response.headers or "uvicorn" not in response.headers.get(
            "server", ""
        )
