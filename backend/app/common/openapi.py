"""运行时 OpenAPI 的认证边界补充。"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from typing import cast

from fastapi import FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute

from app.auth.dependencies import get_current_user

_HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
_ERROR_SCHEMA_REF = {"$ref": "#/components/schemas/APIErrorResponse"}


def _mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError("OpenAPI 节点必须是对象")
    return cast(dict[str, object], value)


def _uses_current_user(dependant: Dependant) -> bool:
    return any(
        dependency.call is get_current_user or _uses_current_user(dependency)
        for dependency in dependant.dependencies
    )


def _iter_schema_routes(app: FastAPI) -> Iterator[tuple[str, set[str], Dependant]]:
    """兼容 FastAPI 延迟展开的 include_router 路由。"""
    for route in app.routes:
        if isinstance(route, APIRoute):
            candidates: Iterable[object] = (route,)
        else:
            candidate_factory = getattr(route, "effective_candidates", None)
            if not callable(candidate_factory):
                continue
            candidates = cast(
                Callable[[], Iterable[object]], candidate_factory
            )()

        for candidate in candidates:
            path = getattr(candidate, "path", None)
            methods = getattr(candidate, "methods", None)
            dependant = getattr(candidate, "dependant", None)
            if (
                not isinstance(path, str)
                or not isinstance(methods, set)
                or not isinstance(dependant, Dependant)
            ):
                continue
            yield path, {method for method in methods if isinstance(method, str)}, dependant


def build_openapi_schema(app: FastAPI) -> dict[str, object]:
    """生成带 Bearer security 与通用鉴权错误说明的完整运行时契约。"""
    schema = _mapping(
        get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
    )
    components = _mapping(schema.setdefault("components", {}))
    security_schemes = _mapping(components.setdefault("securitySchemes", {}))
    security_schemes["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    component_schemas = _mapping(components.setdefault("schemas", {}))
    component_schemas["APIErrorResponse"] = {
        "type": "object",
        "title": "APIErrorResponse",
        "description": "所有非健康检查 API 的统一错误响应。",
        "required": ["code", "message", "data", "request_id"],
        "properties": {
            "code": {"type": "integer"},
            "message": {"type": "string"},
            "data": {"type": "null"},
            "request_id": {"type": "string"},
        },
    }

    paths = _mapping(schema.get("paths", {}))
    for path_item_value in paths.values():
        path_item = _mapping(path_item_value)
        for method, operation_value in path_item.items():
            if method not in _HTTP_METHODS or not isinstance(operation_value, dict):
                continue
            operation = _mapping(operation_value)
            responses = _mapping(operation.setdefault("responses", {}))
            if "422" in responses:
                responses["422"] = {
                    "description": "请求参数错误",
                    "content": {"application/json": {"schema": _ERROR_SCHEMA_REF}},
                }

    for path, methods, dependant in _iter_schema_routes(app):
        if not _uses_current_user(dependant):
            continue
        path_item = _mapping(paths.get(path, {}))
        for method in methods:
            operation_value = path_item.get(method.lower())
            if operation_value is None:
                continue
            operation = _mapping(operation_value)
            operation["security"] = [{"BearerAuth": []}]
            responses = _mapping(operation.setdefault("responses", {}))
            responses.setdefault(
                "401",
                {
                    "description": "未登录、Token 无效或已过期",
                    "content": {"application/json": {"schema": _ERROR_SCHEMA_REF}},
                },
            )
            responses.setdefault(
                "403",
                {
                    "description": "已登录但权限不足",
                    "content": {"application/json": {"schema": _ERROR_SCHEMA_REF}},
                },
            )
    return schema


def install_openapi_schema(app: FastAPI) -> None:
    def custom_openapi() -> dict[str, object]:
        if app.openapi_schema is None:
            app.openapi_schema = build_openapi_schema(app)
        return cast(dict[str, object], app.openapi_schema)

    app.openapi = custom_openapi  # type: ignore[method-assign]
