"""内建授权初始化与首管理员安全边界回归测试。"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.common.seed as seed_module
import scripts.bootstrap_admin as bootstrap_module
from app.auth.router import register_endpoint
from app.auth.schemas import RegisterRequest
from app.common.exceptions import AppException
from app.common.models import Permission, Role, User
from app.models.repository import ModelProvider


def _result(value: object) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


async def test_seed_permissions_corrects_existing_metadata() -> None:
    permissions = [Permission(**data) for data in seed_module.DEFAULT_PERMISSIONS]
    permissions[0].name = "遗留名称"
    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock(side_effect=[_result(item) for item in permissions])
    db.commit = AsyncMock()

    seeded = await seed_module.seed_permissions(db)

    assert seeded == permissions
    assert permissions[0].name == seed_module.DEFAULT_PERMISSIONS[0]["name"]
    db.add.assert_not_called()
    db.commit.assert_awaited_once()


async def test_upsert_role_replaces_legacy_permissions() -> None:
    legacy = Permission(code="legacy.permission", name="遗留", module="legacy", action="use")
    current = Permission(code="chat.use", name="使用问答", module="chat", action="use")
    role = Role(name="普通用户", description="旧描述", status="disabled")
    role.permissions = [legacy]
    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock(return_value=_result(role))
    db.flush = AsyncMock()

    updated = await seed_module._upsert_role(
        db,
        name="普通用户",
        description="当前描述",
        permissions=[current],
    )

    assert updated is role
    assert role.status == "active"
    assert role.description == "当前描述"
    assert role.permissions == [current]
    db.flush.assert_awaited_once()


async def test_builtin_roles_use_exact_permission_allowlists(monkeypatch) -> None:
    permissions = [Permission(**data) for data in seed_module.DEFAULT_PERMISSIONS]
    upsert_role = AsyncMock(
        side_effect=lambda _db, *, name, description, permissions: Role(
            name=name,
            description=description,
            status="active",
        )
    )
    monkeypatch.setattr(
        seed_module,
        "seed_permissions",
        AsyncMock(return_value=permissions),
    )
    monkeypatch.setattr(seed_module, "_upsert_role", upsert_role)
    db = MagicMock(spec=AsyncSession)
    db.commit = AsyncMock()

    await seed_module.seed_builtin_authorization(db)

    permissions_by_role = {
        call.kwargs["name"]: {item.code for item in call.kwargs["permissions"]}
        for call in upsert_role.await_args_list
    }
    all_codes = {item["code"] for item in seed_module.DEFAULT_PERMISSIONS}
    assert permissions_by_role[seed_module.SUPER_ADMIN_ROLE_NAME] == all_codes
    assert (
        permissions_by_role[seed_module.DEFAULT_USER_ROLE_NAME]
        == seed_module.DEFAULT_USER_PERMISSION_CODES
    )
    assert (
        permissions_by_role[seed_module.KNOWLEDGE_EDITOR_ROLE_NAME]
        == seed_module.KNOWLEDGE_EDITOR_PERMISSION_CODES
    )
    assert "admin.export.cleanup" not in seed_module.DEFAULT_USER_PERMISSION_CODES
    assert "admin.export.cleanup" not in seed_module.KNOWLEDGE_EDITOR_PERMISSION_CODES
    db.commit.assert_awaited_once()


@pytest.mark.parametrize(
    ("enabled", "password"),
    [(False, "long-enough-demo-password"), (True, "too-short")],
)
async def test_demo_seed_refuses_configuration_bypass(
    monkeypatch,
    enabled: bool,
    password: str,
) -> None:
    monkeypatch.setattr(seed_module.settings, "auto_seed_demo_data", enabled)
    monkeypatch.setattr(seed_module.settings, "demo_seed_password", password)
    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock(side_effect=AssertionError("should not query database"))

    with pytest.raises(RuntimeError, match="AUTO_SEED_DEMO_DATA"):
        await seed_module.seed_demo_accounts(db)

    db.execute.assert_not_awaited()


async def test_demo_upsert_resets_existing_password(monkeypatch) -> None:
    user = User(
        username="demo",
        display_name="旧名称",
        password_hash="old-hash",
        status="disabled",
    )
    role = Role(name="普通用户", status="active")
    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock(return_value=_result(user))
    db.flush = AsyncMock()
    monkeypatch.setattr(seed_module, "hash_password", lambda _password: "new-hash")

    updated = await seed_module._upsert_user(
        db,
        username="demo",
        display_name="新名称",
        password="not-returned-or-logged",
        roles=[role],
    )

    assert updated.password_hash == "new-hash"
    assert updated.status == "active"
    assert updated.roles == [role]


async def test_seed_model_providers_creates_configured_definitions(monkeypatch) -> None:
    monkeypatch.setattr(seed_module.settings, "deepseek_base_url", "https://api.minimax.io/v1")
    monkeypatch.setattr(seed_module.settings, "deepseek_chat_model", "MiniMax-M3")
    monkeypatch.setattr(
        seed_module.settings,
        "dashscope_base_url",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    db = MagicMock(spec=AsyncSession)
    db.get = AsyncMock(return_value=None)
    db.commit = AsyncMock()

    await seed_module.seed_model_providers(db)

    added = [call.args[0] for call in db.add.call_args_list]
    assert [(item.code, item.display_name, item.base_url) for item in added[:2]] == [
        ("deepseek", "MiniMax", "https://api.minimax.io/v1"),
        (
            "dashscope",
            "阿里云 DashScope",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ),
    ]
    assert [item.code for item in added] == [
        "deepseek",
        "dashscope",
        "moonshot",
        "zhipu",
        "minimax",
        "volcengine",
        "qianfan",
        "openai",
    ]
    assert all(isinstance(item, ModelProvider) and item.enabled for item in added)
    db.commit.assert_awaited_once()
    db.execute.assert_not_called()


async def test_seed_model_providers_preserves_existing_definitions(monkeypatch) -> None:
    deepseek = ModelProvider(
        code="deepseek",
        display_name="旧名称",
        base_url="https://old.example.com",
        enabled=False,
    )
    dashscope = ModelProvider(
        code="dashscope",
        display_name="旧名称",
        base_url="https://old.example.com",
        enabled=False,
    )
    monkeypatch.setattr(seed_module.settings, "deepseek_base_url", "https://api.deepseek.com")
    monkeypatch.setattr(seed_module.settings, "deepseek_chat_model", "deepseek-chat")
    monkeypatch.setattr(
        seed_module.settings,
        "dashscope_base_url",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    providers = {
        "deepseek": deepseek,
        "dashscope": dashscope,
        "moonshot": ModelProvider(code="moonshot", display_name="Moonshot"),
        "zhipu": ModelProvider(code="zhipu", display_name="Zhipu"),
        "minimax": ModelProvider(code="minimax", display_name="MiniMax"),
        "volcengine": ModelProvider(code="volcengine", display_name="Volcengine"),
        "qianfan": ModelProvider(code="qianfan", display_name="Qianfan"),
        "openai": ModelProvider(code="openai", display_name="OpenAI"),
    }
    db = MagicMock(spec=AsyncSession)
    db.get = AsyncMock(side_effect=lambda _model, code: providers[code])
    db.commit = AsyncMock()

    await seed_module.seed_model_providers(db)

    assert (deepseek.display_name, deepseek.base_url, deepseek.enabled) == (
        "旧名称",
        "https://old.example.com",
        False,
    )
    assert (dashscope.display_name, dashscope.base_url, dashscope.enabled) == (
        "旧名称",
        "https://old.example.com",
        False,
    )
    db.add.assert_not_called()
    db.commit.assert_awaited_once()
    db.execute.assert_not_called()


async def test_register_returns_503_when_default_role_is_missing() -> None:
    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock(return_value=_result(None))

    with pytest.raises(AppException) as exc_info:
        await register_endpoint(
            RegisterRequest(
                username="new-user",
                display_name="新用户",
                password="test-password",
            ),
            db,
        )

    assert exc_info.value.status_code == 503
    assert "基础角色初始化" in exc_info.value.message


async def test_bootstrap_refuses_when_admin_already_exists(monkeypatch) -> None:
    role = Role(id="admin-role", name=seed_module.SUPER_ADMIN_ROLE_NAME, status="active")
    monkeypatch.setattr(
        bootstrap_module,
        "seed_builtin_authorization",
        AsyncMock(return_value={seed_module.SUPER_ADMIN_ROLE_NAME: role}),
    )
    monkeypatch.setattr(bootstrap_module, "_admin_exists", AsyncMock(return_value=True))
    db = MagicMock(spec=AsyncSession)

    with pytest.raises(RuntimeError, match="已存在管理员"):
        await bootstrap_module._prepare_bootstrap(db)
