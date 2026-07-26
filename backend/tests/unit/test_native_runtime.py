"""原生核心启动边界测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.native import runtime


def test_development_can_run_without_native_core() -> None:
    runtime.enforce_native_core(
        required=False,
        license_required=False,
        license_file="",
    )


def test_required_native_core_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime, "native_core_loaded", lambda: False)

    with pytest.raises(RuntimeError, match="原生核心未加载"):
        runtime.enforce_native_core(
            required=True,
            license_required=False,
            license_file="",
        )


def test_required_license_only_exposes_boolean_status(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    license_file = tmp_path / "license.json"
    license_file.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(runtime, "native_core_loaded", lambda: True)
    monkeypatch.setattr(runtime, "_native_license_is_valid", lambda _path: False)

    with pytest.raises(RuntimeError, match="许可证无效"):
        runtime.enforce_native_core(
            required=True,
            license_required=True,
            license_file=str(license_file),
        )
