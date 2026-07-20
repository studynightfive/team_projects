"""Office/EPUB 压缩容器的资源边界回归测试。"""

from __future__ import annotations

import zipfile

import pytest

from app.common.config import settings
from app.common.exceptions import AppException
from app.parsers.archive import validate_zip_container


def test_valid_zip_container_passes(tmp_path) -> None:
    path = tmp_path / "valid.docx"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", "<document>ok</document>")
    validate_zip_container(str(path))


def test_zip_container_rejects_total_uncompressed_limit(tmp_path, monkeypatch) -> None:
    path = tmp_path / "oversized.docx"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", "x" * 64)
    monkeypatch.setattr(settings, "archive_max_uncompressed_bytes", 32)
    with pytest.raises(AppException, match="总量过大"):
        validate_zip_container(str(path))


def test_zip_container_rejects_traversal_entry(tmp_path) -> None:
    path = tmp_path / "traversal.epub"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("../outside.txt", "unsafe")
    with pytest.raises(AppException, match="非法路径"):
        validate_zip_container(str(path))


def test_zip_container_rejects_invalid_archive(tmp_path) -> None:
    path = tmp_path / "broken.xlsx"
    path.write_bytes(b"not-a-zip")
    with pytest.raises(AppException, match="格式无效"):
        validate_zip_container(str(path))
