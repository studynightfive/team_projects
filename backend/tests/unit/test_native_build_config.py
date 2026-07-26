"""原生核心构建参数测试。"""

from __future__ import annotations

import pytest

from scripts.build_native import _license_public_key


def test_native_build_allows_empty_public_key_for_local_demo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NATIVE_LICENSE_PUBLIC_KEY_HEX", raising=False)

    assert _license_public_key() == ""


def test_native_build_rejects_invalid_public_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NATIVE_LICENSE_PUBLIC_KEY_HEX", "not-a-public-key")

    with pytest.raises(SystemExit, match="64 位十六进制公钥"):
        _license_public_key()


def test_native_build_normalizes_valid_public_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NATIVE_LICENSE_PUBLIC_KEY_HEX", "AB" * 32)

    assert _license_public_key() == "ab" * 32
