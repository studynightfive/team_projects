"""静态 OpenAPI 与运行时 FastAPI 路由的一致性测试。"""

from pathlib import Path

import yaml

from app.main import app

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SPEC_PATH = PROJECT_ROOT / "docs" / "api" / "openapi.yaml"


def load_openapi_spec() -> dict:
    with SPEC_PATH.open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def normalized_runtime_spec() -> dict:
    schema = app.openapi()
    schema["servers"] = [{"url": "/api/v1", "description": "API 前缀"}]
    schema["paths"] = {
        path.removeprefix("/api/v1"): value
        for path, value in schema["paths"].items()
        if path.startswith("/api/v1")
    }
    return schema


def test_openapi_file_exists() -> None:
    assert SPEC_PATH.is_file()


def test_static_openapi_matches_runtime_contract() -> None:
    static = load_openapi_spec()
    runtime = normalized_runtime_spec()

    assert static == runtime


def test_static_openapi_declares_bearer_security() -> None:
    static = load_openapi_spec()
    scheme = static["components"]["securitySchemes"]["BearerAuth"]
    assert scheme == {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    assert static["paths"]["/me"]["get"]["security"] == [{"BearerAuth": []}]
    assert "security" not in static["paths"]["/auth/login"]["post"]
    assert "/" not in static["paths"]


def test_static_openapi_uses_unified_error_schema() -> None:
    static = load_openapi_spec()
    error_schema = static["components"]["schemas"]["APIErrorResponse"]
    assert error_schema["required"] == ["code", "message", "data", "request_id"]
    assert static["paths"]["/auth/login"]["post"]["responses"]["422"] == {
        "description": "请求参数错误",
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/APIErrorResponse"}
            }
        },
    }
