"""模型与检索评测管理接口的权限边界回归测试。"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.auth.dependencies import get_current_user
from app.common.models import Permission, Role, User
from app.main import app


@pytest.fixture
def legacy_management_user() -> Iterator[None]:
    """即使历史角色仍带旧权限码，也不能进入管理接口。"""
    permissions = [
        Permission(
            id=f"permission-{index}",
            code=code,
            name=code,
            module="legacy",
            action="legacy",
        )
        for index, code in enumerate(
            (
                "model:read",
                "model:write",
                "model:test",
                "retrieval_test:read",
                "retrieval_test:write",
                "retrieval_test:run",
            )
        )
    ]
    role = Role(
        id="role-legacy-user",
        name="历史普通用户",
        description="仅用于权限回归测试",
        status="active",
        permissions=permissions,
    )
    user = User(
        id="user-legacy-user",
        username="legacy-user",
        display_name="历史普通用户",
        password_hash="not-used",
        status="active",
        roles=[role],
    )
    previous_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        yield
    finally:
        app.dependency_overrides = previous_overrides


MODEL_REQUESTS: tuple[tuple[str, str, dict[str, object] | None], ...] = (
    ("GET", "/api/v1/models/providers", None),
    (
        "POST",
        "/api/v1/models/providers",
        {
            "code": "custom",
            "display_name": "Custom",
            "base_url": "https://api.example.com/v1",
            "enabled": True,
        },
    ),
    (
        "PATCH",
        "/api/v1/models/providers/custom",
        {"display_name": "Updated"},
    ),
    ("DELETE", "/api/v1/models/providers/custom", None),
    ("GET", "/api/v1/models", None),
    (
        "POST",
        "/api/v1/models",
        {
            "provider_code": "custom",
            "model_name": "test-model",
            "kind": "chat",
        },
    ),
    ("PATCH", "/api/v1/models/model-id", {"enabled": False}),
    ("DELETE", "/api/v1/models/model-id", None),
    ("POST", "/api/v1/models/model-id/test", None),
)


@pytest.mark.parametrize(("method", "path", "payload"), MODEL_REQUESTS)
async def test_legacy_model_permissions_cannot_access_admin_routes(
    client: AsyncClient,
    legacy_management_user: None,
    method: str,
    path: str,
    payload: dict[str, object] | None,
) -> None:
    response = await client.request(method, path, json=payload)
    assert response.status_code == 403


async def test_legacy_retrieval_test_permission_cannot_access_admin_route(
    client: AsyncClient,
    legacy_management_user: None,
) -> None:
    response = await client.get("/api/v1/retrieval-tests/datasets")
    assert response.status_code == 403


def test_contract_uses_expected_application() -> None:
    assert isinstance(app, FastAPI)
