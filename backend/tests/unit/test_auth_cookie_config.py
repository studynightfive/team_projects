"""Refresh Cookie 与服务端有效期配置一致。"""

from app.auth.router import _refresh_cookie_max_age
from app.common.config import settings


def test_refresh_cookie_max_age_uses_settings(monkeypatch) -> None:
    monkeypatch.setattr(settings, "refresh_token_expire_days", 3)
    assert _refresh_cookie_max_age() == 3 * 24 * 3600
