"""员工5 提示词 01 - 模型管理单元测试

覆盖：
- Fernet 加解密往返（永远不回显明文）
- Provider 工厂与连通性测试的边界
- 业务逻辑：provider / model CRUD + 密钥写后无明文残留
- Schemas：只写字段约束
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import get_model_key_fernet
from app.models import service as model_service
from app.models.providers.openai import OpenAICompatibleProvider, build_provider
from app.models.repository import Model, ModelProvider
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
    @pytest.mark.parametrize("code", ["openai", "deepseek", "ollama", "custom", "anthropic"])
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
    async def test_dashscope_rerank_uses_compatible_reranks_endpoint(self, monkeypatch):
        captured_url = ""

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_url
            captured_url = str(request.url)
            return httpx.Response(
                200,
                json={"results": [{"index": 0, "relevance_score": 0.91}]},
            )

        client = httpx.AsyncClient(
            base_url="https://dashscope.aliyuncs.com/compatible-api/v1",
            transport=httpx.MockTransport(handler),
        )
        provider = OpenAICompatibleProvider(
            "dashscope",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "test-key",
        )
        monkeypatch.setattr(
            "app.models.providers.openai.settings.dashscope_rerank_base_url",
            "https://dashscope.aliyuncs.com/compatible-api/v1",
        )
        monkeypatch.setattr(provider, "_validate_resolved_host", AsyncMock())
        monkeypatch.setattr(provider, "_client_create", lambda **_kwargs: client)

        result = await provider.rerank(
            model_name="qwen3-rerank",
            query="患者数据安全",
            documents=["使用访问控制与审计"],
            top_n=1,
        )

        assert captured_url.endswith("/compatible-api/v1/reranks")
        assert result == [{"index": 0, "relevance_score": 0.91}]

    @pytest.mark.asyncio
    async def test_returns_ok_on_200(self):
        p = OpenAICompatibleProvider("openai", "https://api.openai.com/v1", "sk-x")
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status_code = 200
            mock_get.return_value = mock_resp
            result = await p.test(
                model_name="gpt-4o-mini", api_key="sk-x", base_url="https://api.openai.com/v1"
            )
        assert result["ok"] is True
        assert result["latency_ms"] >= 0
        assert result["model_info"]["status_code"] == 200
        assert result["model_info"]["authenticated"] is True
        assert result["model_info"]["model_name"] == "gpt-4o-mini"
        assert result["model_info"]["model_entitlement_checked"] is False

    @pytest.mark.asyncio
    async def test_missing_api_key_does_not_send_request(self):
        p = OpenAICompatibleProvider("openai", "https://api.openai.com/v1", "")
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            result = await p.test(
                model_name="gpt-4o-mini", api_key="", base_url="https://api.openai.com/v1"
            )
        assert result["ok"] is False
        assert result["error_code"] == "missing_api_key"
        mock_get.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_returns_authentication_failure_on_401(self):
        """认证失败不能被误报为模型可用。"""
        p = OpenAICompatibleProvider("openai", "https://api.openai.com/v1", "sk-x")
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status_code = 401
            mock_get.return_value = mock_resp
            result = await p.test(
                model_name="x", api_key="sk-x", base_url="https://api.openai.com/v1"
            )
        assert result["ok"] is False
        assert result["error_code"] == "authentication_failed"

    @pytest.mark.asyncio
    async def test_returns_error_on_500(self):
        p = OpenAICompatibleProvider("openai", "https://api.openai.com/v1", "sk-x")
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status_code = 500
            mock_get.return_value = mock_resp
            result = await p.test(
                model_name="x", api_key="sk-x", base_url="https://api.openai.com/v1"
            )
        assert result["ok"] is False
        assert result["error_code"] == "provider_unreachable"

    @pytest.mark.asyncio
    async def test_network_exception_yields_network_error(self):
        p = OpenAICompatibleProvider("openai", "https://api.openai.com/v1", "sk-x")
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = ConnectionError("refused")
            result = await p.test(
                model_name="x", api_key="sk-x", base_url="https://api.openai.com/v1"
            )
        assert result["ok"] is False
        assert result["error_code"] == "network_error"
        assert "refused" not in result["error_message"]


# ============================================================
# 业务逻辑 - mock DB
# ============================================================
class TestModelService:
    """业务逻辑层：用 AsyncMock 模拟 AsyncSession，避免真实数据库。"""

    @pytest.mark.asyncio
    async def test_create_model_encrypts_api_key(self):
        db = MagicMock(spec=AsyncSession)
        # get_provider 存在
        provider_obj = AsyncMock()
        provider_obj.code = "openai"
        db.get.return_value = provider_obj

        from app.models.schemas import ModelCreate

        payload = ModelCreate(
            provider_code="openai",
            model_name="gpt-4o-mini",
            kind="chat",
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
        db = MagicMock(spec=AsyncSession)
        provider_obj = AsyncMock()
        provider_obj.code = "openai"
        db.get.return_value = provider_obj

        from app.models.schemas import ModelCreate

        payload = ModelCreate(provider_code="openai", model_name="m", kind="chat")
        model = await model_service.create_model(db, payload)
        assert model.api_key_encrypted is None

    @pytest.mark.asyncio
    async def test_create_model_unknown_provider_raises(self):
        db = MagicMock(spec=AsyncSession)
        db.get.return_value = None  # provider 不存在（schema 已限定为合法枚举）

        from app.common.exceptions import ValidationException
        from app.models.schemas import ModelCreate

        payload = ModelCreate(provider_code="openai", model_name="x", kind="chat")
        with pytest.raises(ValidationException):
            await model_service.create_model(db, payload)

    @pytest.mark.asyncio
    async def test_update_model_replaces_key(self):
        db = MagicMock(spec=AsyncSession)
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
        db = MagicMock(spec=AsyncSession)
        provider_obj = AsyncMock()
        provider_obj.code = "openai"
        db.get.return_value = provider_obj
        # 存在关联 model
        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none.return_value = AsyncMock()  # 存在
        db.execute.return_value = scalar_result

        from app.common.exceptions import ConflictException

        with pytest.raises(ConflictException):
            await model_service.delete_provider(db, "openai")

    @pytest.mark.asyncio
    async def test_chat_model_test_invokes_selected_model(self):
        db = MagicMock(spec=AsyncSession)
        model = MagicMock(spec=Model)
        model.provider_code = "deepseek"
        model.model_name = "deepseek-v4-pro"
        model.kind = "chat"
        model.parameters = {"max_tokens": 1200}
        model.api_key_encrypted = encrypt_api_key("test-key")
        provider = MagicMock(spec=ModelProvider)
        provider.code = "deepseek"
        provider.base_url = "https://api.deepseek.com"
        provider.enabled = True
        db.get = AsyncMock(side_effect=[model, provider])
        client = MagicMock(spec=OpenAICompatibleProvider)
        client.chat = AsyncMock(return_value="连接正常")

        with patch("app.models.service.build_provider", return_value=client):
            result = await model_service.test_model(db, "model-1")

        assert result.ok is True
        client.chat.assert_awaited_once()
        assert client.chat.await_args.kwargs["model_name"] == "deepseek-v4-pro"
        assert client.chat.await_args.kwargs["max_tokens"] == 1200

    @pytest.mark.asyncio
    async def test_embedding_model_test_rejects_dimension_mismatch(self):
        db = MagicMock(spec=AsyncSession)
        model = MagicMock(spec=Model)
        model.provider_code = "dashscope"
        model.model_name = "text-embedding-v2"
        model.kind = "embedding"
        model.parameters = {}
        model.dimensions = 1536
        model.api_key_encrypted = encrypt_api_key("test-key")
        provider = MagicMock(spec=ModelProvider)
        provider.code = "dashscope"
        provider.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        provider.enabled = True
        db.get = AsyncMock(side_effect=[model, provider])
        client = MagicMock(spec=OpenAICompatibleProvider)
        client.embed = AsyncMock(return_value=[[0.1, 0.2, 0.3]])

        with patch("app.models.service.build_provider", return_value=client):
            result = await model_service.test_model(db, "model-2")

        assert result.ok is False
        assert result.error_code == "dimension_mismatch"
        assert "1536" in (result.error_message or "")

    @pytest.mark.asyncio
    async def test_rerank_model_test_invokes_rerank_endpoint(self):
        db = MagicMock(spec=AsyncSession)
        model = MagicMock(spec=Model)
        model.provider_code = "dashscope"
        model.model_name = "qwen3-rerank"
        model.kind = "rerank"
        model.parameters = {}
        model.top_n = 10
        model.api_key_encrypted = encrypt_api_key("test-key")
        provider = MagicMock(spec=ModelProvider)
        provider.code = "dashscope"
        provider.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        provider.enabled = True
        db.get = AsyncMock(side_effect=[model, provider])
        client = MagicMock(spec=OpenAICompatibleProvider)
        client.rerank = AsyncMock(return_value=[{"index": 0, "relevance_score": 0.95}])

        with patch("app.models.service.build_provider", return_value=client):
            result = await model_service.test_model(db, "model-3")

        assert result.ok is True
        client.rerank.assert_awaited_once()


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
