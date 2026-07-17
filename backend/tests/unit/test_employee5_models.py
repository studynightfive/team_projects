"""员工5 提示词 01 - 模型管理单元测试

覆盖：
- Fernet 加解密往返（永远不回显明文）
- Provider 工厂与连通性测试的边界
- 业务逻辑：provider / model CRUD + 密钥写后无明文残留
- Schemas：只写字段约束
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.common.config import get_model_key_fernet
from app.models import service as model_service
from app.models.providers.openai import OpenAICompatibleProvider, build_provider
from app.models.security import decrypt_api_key, encrypt_api_key


# ============================================================
# Fernet 加解密（安全基线）
# ============================================================
class TestFernetCrypto:
    def test_roundtrip_basic(self):
        plain = "sk-test-abc-1234567890"
        enc = encrypt_api_key(plain)
        assert enc != plain
        assert decrypt_api_key(enc) == plain

    def test_empty_string_returns_empty(self):
        assert encrypt_api_key("") == ""
        assert decrypt_api_key("") == ""

    def test_two_encrypts_differ_for_same_plain(self):
        """Fernet 使用随机 IV，相同明文两次加密结果应不同"""
        a = encrypt_api_key("sk-same")
        b = encrypt_api_key("sk-same")
        assert a != b
        assert decrypt_api_key(a) == decrypt_api_key(b) == "sk-same"

    def test_fernet_singleton(self):
        f1 = get_model_key_fernet()
        f2 = get_model_key_fernet()
        assert f1 is f2


# ============================================================
# Provider 工厂
# ============================================================
class TestProviderFactory:
    @pytest.mark.parametrize(
        "code", ["openai", "deepseek", "ollama", "custom", "anthropic"]
    )
    def test_known_providers(self, code):
        p = build_provider(code, "https://api.example.com/v1", "key", timeout=5.0)
        assert isinstance(p, OpenAICompatibleProvider)
        assert p.provider_code == code
        assert p.timeout == 5.0

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="unsupported"):
            build_provider("unknown-xyz", "https://x", "k")


# ============================================================
# Provider 连通性测试（mock HTTP）
# ============================================================
class TestProviderTest:
    @pytest.mark.asyncio
    async def test_returns_ok_on_200(self):
        from app.models.schemas import TestModelResponse

        p = OpenAICompatibleProvider("openai", "https://api.openai.com/v1", "sk-x")
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status_code = 200
            mock_get.return_value = mock_resp
            result = await p.test(model_name="gpt-4o-mini", api_key="sk-x", base_url="https://api.openai.com/v1")
        assert result["ok"] is True
        assert result["latency_ms"] >= 0
        assert result["model_info"]["status_code"] == 200

    @pytest.mark.asyncio
    async def test_returns_401_as_ok_with_flag(self):
        """401 表示鉴权失败但服务可达，不算网络错误"""
        p = OpenAICompatibleProvider("openai", "https://api.openai.com/v1", "sk-x")
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status_code = 401
            mock_get.return_value = mock_resp
            result = await p.test(model_name="x", api_key="sk-x", base_url="https://api.openai.com/v1")
        assert result["ok"] is True
        assert result["model_info"]["status_code"] == 401

    @pytest.mark.asyncio
    async def test_returns_error_on_500(self):
        p = OpenAICompatibleProvider("openai", "https://api.openai.com/v1", "sk-x")
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status_code = 500
            mock_get.return_value = mock_resp
            result = await p.test(model_name="x", api_key="sk-x", base_url="https://api.openai.com/v1")
        assert result["ok"] is False
        assert result["error_code"] == "provider_unreachable"

    @pytest.mark.asyncio
    async def test_network_exception_yields_network_error(self):
        p = OpenAICompatibleProvider("openai", "https://api.openai.com/v1", "sk-x")
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = ConnectionError("refused")
            result = await p.test(model_name="x", api_key="sk-x", base_url="https://api.openai.com/v1")
        assert result["ok"] is False
        assert result["error_code"] == "network_error"
        assert "refused" in result["error_message"]


# ============================================================
# 业务逻辑 - mock DB
# ============================================================
class TestModelService:
    """业务逻辑层：用 AsyncMock 模拟 AsyncSession，避免真实数据库。"""

    @pytest.mark.asyncio
    async def test_create_model_encrypts_api_key(self):
        db = AsyncMock()
        # get_provider 存在
        provider_obj = AsyncMock()
        provider_obj.code = "openai"
        db.get.return_value = provider_obj

        from app.models.schemas import ModelCreate

        payload = ModelCreate(
            provider_code="openai", model_name="gpt-4o-mini", kind="chat",
            api_key="sk-plaintext-12345",
        )
        model = await model_service.create_model(db, payload)

        assert model.api_key_encrypted != "sk-plaintext-12345"
        assert model.api_key_encrypted  # 非空
        assert decrypt_api_key(model.api_key_encrypted) == "sk-plaintext-12345"
        # db.add 被调用
        db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_model_no_api_key_stays_empty(self):
        db = AsyncMock()
        provider_obj = AsyncMock()
        provider_obj.code = "openai"
        db.get.return_value = provider_obj

        from app.models.schemas import ModelCreate

        payload = ModelCreate(provider_code="openai", model_name="m", kind="chat")
        model = await model_service.create_model(db, payload)
        assert model.api_key_encrypted is None

    @pytest.mark.asyncio
    async def test_create_model_unknown_provider_raises(self):
        db = AsyncMock()
        db.get.return_value = None  # provider 不存在（schema 已限定为合法枚举）

        from app.common.exceptions import ValidationException
        from app.models.schemas import ModelCreate

        payload = ModelCreate(provider_code="openai", model_name="x", kind="chat")
        with pytest.raises(ValidationException):
            await model_service.create_model(db, payload)

    @pytest.mark.asyncio
    async def test_update_model_replaces_key(self):
        db = AsyncMock()
        existing = AsyncMock()
        existing.api_key_encrypted = encrypt_api_key("old-key")
        existing.model_name = "gpt-4o-mini"
        existing.parameters = {}
        existing.enabled = True
        existing.dimensions = None
        existing.distance = None
        existing.top_n = None
        db.get.return_value = existing

        from app.models.schemas import ModelUpdate

        payload = ModelUpdate(api_key="new-key-999")
        model = await model_service.update_model(db, "m1", payload)
        assert decrypt_api_key(model.api_key_encrypted) == "new-key-999"

    @pytest.mark.asyncio
    async def test_delete_provider_with_models_raises_conflict(self):
        db = AsyncMock()
        provider_obj = AsyncMock()
        provider_obj.code = "openai"
        db.get.return_value = provider_obj
        # 存在关联 model
        scalar_result = AsyncMock()
        scalar_result.scalar_one_or_none.return_value = AsyncMock()  # 存在
        db.execute.return_value = scalar_result

        from app.common.exceptions import ConflictException

        with pytest.raises(ConflictException):
            await model_service.delete_provider(db, "openai")


# ============================================================
# Schemas - api_key 只写不回显
# ============================================================
class TestModelSchemas:
    def test_model_create_accepts_api_key(self):
        from app.models.schemas import ModelCreate

        m = ModelCreate(provider_code="openai", model_name="m", kind="chat", api_key="plain")
        assert m.api_key == "plain"

    def test_model_response_never_exposes_plain_key(self):
        """响应 schema 必须只有 api_key_set 布尔标志，绝不含明文字段。"""
        from app.models.schemas import ModelResponse

        fields = ModelResponse.model_fields.keys()
        assert "api_key" not in fields
        assert "api_key_encrypted" not in fields
        assert "api_key_set" in fields
        assert "api_key_plain" not in fields
        assert "api_key_value" not in fields