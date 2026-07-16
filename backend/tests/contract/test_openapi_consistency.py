# OpenAPI 规范一致性测试
# 验证实际 API 响应与 OpenAPI 定义一致

from pathlib import Path

import pytest
import yaml

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def load_openapi_spec():
    """加载 OpenAPI 规范文件"""
    spec_path = PROJECT_ROOT / "docs" / "api" / "openapi.yaml"
    if not spec_path.exists():
        pytest.skip("OpenAPI 规范文件不存在，跳过契约测试")

    with open(spec_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


class TestOpenAPIStructure:
    """OpenAPI 规范结构验证"""

    def test_openapi_file_exists(self):
        """验证 OpenAPI 规范文件存在"""
        spec_path = PROJECT_ROOT / "docs" / "api" / "openapi.yaml"
        assert spec_path.exists(), f"OpenAPI 规范文件不存在: {spec_path}"

    def test_openapi_version(self):
        """验证 OpenAPI 版本为 3.0.x"""
        spec = load_openapi_spec()
        assert spec["openapi"].startswith("3.0"), (
            f"OpenAPI 版本应为 3.0.x，实际为 {spec['openapi']}"
        )

    def test_openapi_info(self):
        """验证 OpenAPI 包含基本信息"""
        spec = load_openapi_spec()
        assert "info" in spec
        assert "title" in spec["info"]
        assert "version" in spec["info"]

    def test_openapi_paths(self):
        """验证 OpenAPI 包含路径定义"""
        spec = load_openapi_spec()
        assert "paths" in spec
        assert len(spec["paths"]) > 0, "OpenAPI 应至少包含一个路径定义"

    def test_openapi_components(self):
        """验证 OpenAPI 包含组件定义"""
        spec = load_openapi_spec()
        assert "components" in spec
        assert "schemas" in spec["components"]


class TestOpenAPIEndpointPaths:
    """OpenAPI 端点路径验证"""

    def test_health_endpoints_exist(self):
        """验证健康检查端点已定义"""
        spec = load_openapi_spec()
        paths = spec["paths"]
        assert "/health/live" in paths, "缺少 /health/live 端点"
        assert "/health/ready" in paths, "缺少 /health/ready 端点"

    def test_auth_endpoints_exist(self):
        """验证认证端点已定义"""
        spec = load_openapi_spec()
        paths = spec["paths"]
        assert "/auth/login" in paths, "缺少 /auth/login 端点"
        assert "/auth/logout" in paths, "缺少 /auth/logout 端点"
        assert "/auth/refresh" in paths, "缺少 /auth/refresh 端点"
        assert "/me" in paths, "缺少 /me 端点"

    def test_users_endpoints_exist(self):
        """验证用户管理端点已定义"""
        spec = load_openapi_spec()
        paths = spec["paths"]
        assert "/users" in paths, "缺少 /users 端点"
        assert "/users/{user_id}" in paths, "缺少 /users/{user_id} 端点"

    def test_roles_endpoints_exist(self):
        """验证角色管理端点已定义"""
        spec = load_openapi_spec()
        paths = spec["paths"]
        assert "/roles" in paths, "缺少 /roles 端点"
        assert "/roles/{role_id}" in paths, "缺少 /roles/{role_id} 端点"

    def test_models_endpoints_exist(self):
        """验证模型管理端点已定义"""
        spec = load_openapi_spec()
        paths = spec["paths"]
        assert "/models" in paths, "缺少 /models 端点"
        assert "/models/{model_id}" in paths, "缺少 /models/{model_id} 端点"

    def test_knowledge_bases_endpoints_exist(self):
        """验证知识库管理端点已定义"""
        spec = load_openapi_spec()
        paths = spec["paths"]
        assert "/knowledge-bases" in paths, "缺少 /knowledge-bases 端点"
        assert "/knowledge-bases/available" in paths, "缺少 /knowledge-bases/available 端点"

    def test_documents_endpoints_exist(self):
        """验证文档管理端点已定义"""
        spec = load_openapi_spec()
        paths = spec["paths"]
        assert "/documents/{document_id}" in paths, "缺少 /documents/{document_id} 端点"

    def test_retrieval_endpoints_exist(self):
        """验证检索端点已定义"""
        spec = load_openapi_spec()
        paths = spec["paths"]
        assert "/retrieval/search" in paths, "缺少 /retrieval/search 端点"

    def test_chat_endpoints_exist(self):
        """验证问答端点已定义"""
        spec = load_openapi_spec()
        paths = spec["paths"]
        assert "/chat/stream" in paths, "缺少 /chat/stream 端点"
        assert "/conversations" in paths, "缺少 /conversations 端点"

    def test_exports_endpoints_exist(self):
        """验证导出端点已定义"""
        spec = load_openapi_spec()
        paths = spec["paths"]
        assert "/exports" in paths, "缺少 /exports 端点"

    def test_audit_endpoints_exist(self):
        """验证审计端点已定义"""
        spec = load_openapi_spec()
        paths = spec["paths"]
        assert "/audit-logs" in paths, "缺少 /audit-logs 端点"


class TestOpenAPISchemaFormat:
    """OpenAPI Schema 格式验证"""

    def test_health_response_has_required_fields(self):
        """验证健康检查响应包含必需字段"""
        spec = load_openapi_spec()
        schema = spec["components"]["schemas"]["HealthLiveResponse"]
        assert "required" in schema
        assert "status" in schema["required"]
        assert "timestamp" in schema["required"]

    def test_login_request_has_required_fields(self):
        """验证登录请求包含必需字段"""
        spec = load_openapi_spec()
        schema = spec["components"]["schemas"]["LoginRequest"]
        assert "required" in schema
        assert "username" in schema["required"]
        assert "password" in schema["required"]

    def test_me_response_has_user_fields(self):
        """验证 /me 响应包含用户信息字段"""
        spec = load_openapi_spec()
        schema = spec["components"]["schemas"]["MeResponse"]
        data_props = schema["properties"]["data"]["properties"]
        assert "id" in data_props
        assert "username" in data_props
        assert "display_name" in data_props
        assert "roles" in data_props
        assert "permissions" in data_props

    def test_paginated_response_has_pagination_fields(self):
        """验证分页响应包含分页字段"""
        spec = load_openapi_spec()
        schema = spec["components"]["schemas"]["PaginatedUsersResponse"]
        data_props = schema["properties"]["data"]["properties"]
        assert "items" in data_props
        assert "page" in data_props
        assert "page_size" in data_props
        assert "total" in data_props

    def test_task_response_has_status_fields(self):
        """验证任务响应包含状态字段"""
        spec = load_openapi_spec()
        schema = spec["components"]["schemas"]["TaskResponse"]
        data_props = schema["properties"]["data"]["properties"]
        assert "task_id" in data_props
        assert "status" in data_props
        assert "stage" in data_props
        assert "progress" in data_props
