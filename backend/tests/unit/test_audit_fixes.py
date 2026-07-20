"""本轮全项目审计中关键安全边界的回归测试。"""

import pytest
from pydantic import ValidationError

from app.common.config import Settings
from app.common.exceptions import ValidationException
from app.knowledge.schemas import KnowledgeBaseCreate
from app.models.providers.openai import _address_is_allowed, build_provider
from app.models.service import _validate_provider_base_url

SAFE_SETTINGS = {
    "database_url": "postgresql+asyncpg://test:test@localhost/test",
    "secret_key": "test-only-secret-key-with-32-characters",
}


def test_sensitive_settings_have_no_credential_defaults() -> None:
    assert Settings.model_fields["database_url"].is_required()
    assert Settings.model_fields["secret_key"].is_required()
    assert Settings.model_fields["worker_inline"].default is False


def test_production_rejects_demo_seed() -> None:
    with pytest.raises(ValidationError, match="禁止设置 AUTO_SEED_DEMO_DATA"):
        Settings(
            app_environment="production",
            cookie_secure=True,
            auto_seed_demo_data=True,
            demo_seed_password="test-demo-password",
            **SAFE_SETTINGS,
        )


def test_production_requires_secure_cookie() -> None:
    with pytest.raises(ValidationError, match="COOKIE_SECURE=true"):
        Settings(
            app_environment="production",
            cookie_secure=False,
            auto_seed_demo_data=False,
            **SAFE_SETTINGS,
        )


def test_demo_seed_requires_explicit_password() -> None:
    with pytest.raises(ValidationError, match="DEMO_SEED_PASSWORD"):
        Settings(auto_seed_demo_data=True, **SAFE_SETTINGS)


def test_chunk_overlap_must_be_smaller_than_chunk_size() -> None:
    with pytest.raises(ValidationError, match="chunk_overlap 必须小于 chunk_size"):
        KnowledgeBaseCreate(name="invalid", chunk_size=200, chunk_overlap=200)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]:8000",
        "http://api.example.com/v1",
    ],
)
def test_non_ollama_provider_rejects_local_or_unsafe_urls(url: str) -> None:
    with pytest.raises(ValidationException):
        _validate_provider_base_url("custom", url)


def test_ollama_provider_explicitly_allows_local_url() -> None:
    _validate_provider_base_url("ollama", "http://127.0.0.1:11434")


def test_ollama_provider_rejects_link_local_metadata_url() -> None:
    with pytest.raises(ValidationException):
        _validate_provider_base_url("ollama", "http://169.254.169.254/latest/meta-data")


def test_non_ollama_dns_results_must_all_be_public() -> None:
    import ipaddress

    assert _address_is_allowed("custom", "https", ipaddress.ip_address("8.8.8.8"))
    assert not _address_is_allowed("custom", "https", ipaddress.ip_address("10.0.0.1"))


def test_provider_factory_revalidates_stored_base_url() -> None:
    with pytest.raises(ValidationException, match="HTTPS"):
        build_provider("custom", "http://api.example.com/v1", "test-key")
