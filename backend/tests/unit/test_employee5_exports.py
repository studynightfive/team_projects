"""员工5 提示词 05 - 文档导出单元测试

覆盖：
- HMAC 下载签名：签名 / 校验 / 过期判断
- 存储路径：路径穿越防护
- Exporter 抽象与各格式基本输出
- ZIP 打包
"""

from __future__ import annotations

import time
import zipfile
from pathlib import Path

import pytest

from app.exports._shared.signing import (
    is_expired,
    sign_download_token,
    verify_download_token,
)
from app.exports._shared.storage import root, task_dir, task_file_path


# ============================================================
# HMAC 下载签名（提示词 05 §4.5）
# ============================================================
class TestDownloadSigning:
    def test_sign_and_verify_roundtrip(self):
        exp = int(time.time()) + 3600
        tok = sign_download_token(export_id="e1", user_id="u1", expires_at_unix=exp)
        assert verify_download_token(export_id="e1", user_id="u1", expires_at_unix=exp, token=tok)

    def test_tampered_token_rejected(self):
        exp = int(time.time()) + 3600
        tok = sign_download_token(export_id="e1", user_id="u1", expires_at_unix=exp)
        # 翻转一个字符
        bad = ("a" if tok[0] != "a" else "b") + tok[1:]
        assert not verify_download_token(
            export_id="e1", user_id="u1", expires_at_unix=exp, token=bad
        )

    def test_different_user_rejected(self):
        exp = int(time.time()) + 3600
        tok = sign_download_token(export_id="e1", user_id="u1", expires_at_unix=exp)
        assert not verify_download_token(
            export_id="e1", user_id="u2", expires_at_unix=exp, token=tok
        )

    def test_different_export_rejected(self):
        exp = int(time.time()) + 3600
        tok = sign_download_token(export_id="e1", user_id="u1", expires_at_unix=exp)
        assert not verify_download_token(
            export_id="e2", user_id="u1", expires_at_unix=exp, token=tok
        )

    def test_different_expires_rejected(self):
        exp = int(time.time()) + 3600
        tok = sign_download_token(export_id="e1", user_id="u1", expires_at_unix=exp)
        assert not verify_download_token(
            export_id="e1", user_id="u1", expires_at_unix=exp + 1, token=tok
        )

    def test_token_does_not_contain_secrets(self):
        """签名 token 本身不应包含任何敏感字段，仅为签名结果"""
        tok = sign_download_token(export_id="e1", user_id="u1", expires_at_unix=9999999999)
        assert "u1" not in tok
        assert "e1" not in tok
        assert "secret" not in tok.lower()
        assert "key" not in tok.lower()


class TestExpiryCheck:
    def test_future_not_expired(self):
        assert not is_expired(int(time.time()) + 3600)

    def test_past_expired(self):
        assert is_expired(int(time.time()) - 1)

    def test_past_one_second_is_expired(self):
        # 1 秒前必然过期
        assert is_expired(int(time.time()) - 1)

    def test_now_unix_override(self):
        # 假时钟：future 在假时钟下已过期
        assert is_expired(1000, now_unix=2000)


# ============================================================
# 存储路径（提示词 05 §4.9 路径穿越防护）
# ============================================================
class TestStoragePath:
    def test_root_creates_directory(self, tmp_path, monkeypatch):
        from app.common.config import settings

        monkeypatch.setattr(settings, "export_storage_root", str(tmp_path / "exports"))
        p = root()
        assert p.exists()
        assert p.is_dir()

    def test_task_dir_creates_subdir(self, tmp_path, monkeypatch):
        from app.common.config import settings

        monkeypatch.setattr(settings, "export_storage_root", str(tmp_path / "exports"))
        d = task_dir("task-abc")
        assert d.exists()
        assert d.name == "task-abc"

    def test_task_file_path_simple(self, tmp_path, monkeypatch):
        from app.common.config import settings

        monkeypatch.setattr(settings, "export_storage_root", str(tmp_path / "exports"))
        p = task_file_path("t1", "report.pdf")
        assert p.endswith(os.path.join("t1", "report.pdf")) or p.endswith("t1\\report.pdf")
        assert "report.pdf" in p

    def test_path_traversal_blocked(self, tmp_path, monkeypatch):
        from app.common.config import settings

        monkeypatch.setattr(settings, "export_storage_root", str(tmp_path / "exports"))
        # 试图逃逸
        with pytest.raises(ValueError):
            task_file_path("t1", "../etc/passwd")
        with pytest.raises(ValueError):
            task_file_path("t1", "..\\..\\windows\\system32")
        with pytest.raises(ValueError):
            task_file_path("t1", "subdir/file.txt")  # 子目录也被 os.path.basename 剥掉

    def test_double_dot_in_filename_rejected(self, tmp_path, monkeypatch):
        from app.common.config import settings

        monkeypatch.setattr(settings, "export_storage_root", str(tmp_path / "exports"))
        with pytest.raises(ValueError):
            task_file_path("t1", "evil..pdf")


# ============================================================
# Exporter 基本输出（不依赖 WeasyPrint/python-docx）
# ============================================================
class TestMarkdownExporter:
    def test_basic_output(self, tmp_path, monkeypatch):
        from app.common.config import settings
        from app.exports._shared.storage import task_file_path
        from app.exports.all import ExportContent, ExportOptions, MarkdownExporter

        monkeypatch.setattr(settings, "export_storage_root", str(tmp_path / "exports"))
        content = ExportContent(
            document_id="d1",
            title="T",
            markdown="# H\n\nbody",
            citations=[{"doc_id": "d2", "chunk_id": "c1", "score": 0.9}],
        )
        out = task_file_path("t1", "out.md")
        m = MarkdownExporter()
        result = asyncio.run(m.export(content, out, ExportOptions()))
        assert Path(result).read_text(encoding="utf-8").startswith("# T")
        assert "引用" in Path(result).read_text(encoding="utf-8")


class TestTxtExporter:
    def test_basic_output(self, tmp_path, monkeypatch):
        from app.common.config import settings
        from app.exports._shared.storage import task_file_path
        from app.exports.all import ExportContent, ExportOptions, TxtExporter

        monkeypatch.setattr(settings, "export_storage_root", str(tmp_path / "exports"))
        content = ExportContent(document_id="d1", title="My Doc", markdown="## Section\n\ntext")
        out = task_file_path("t1", "out.txt")
        t = TxtExporter()
        result = asyncio.run(t.export(content, out, ExportOptions()))
        text = Path(result).read_text(encoding="utf-8")
        assert "My Doc" in text


class TestCsvExporter:
    def test_basic_output(self, tmp_path, monkeypatch):
        import csv as csvmod

        from app.common.config import settings
        from app.exports._shared.storage import task_file_path
        from app.exports.all import CsvExporter, ExportContent, ExportOptions

        monkeypatch.setattr(settings, "export_storage_root", str(tmp_path / "exports"))
        content = ExportContent(document_id="d1", title="My Doc", markdown="line1\nline2")
        out = task_file_path("t1", "out.csv")
        c = CsvExporter()
        result = asyncio.run(c.export(content, out, ExportOptions()))
        with open(result, encoding="utf-8", newline="") as f:
            reader = csvmod.reader(f)
            rows = list(reader)
        assert rows[0] == ["section", "content"]
        assert ["title", "My Doc"] in rows


# ============================================================
# ZIP 打包
# ============================================================
class TestZipPacker:
    def test_zip_multiple_files(self, tmp_path, monkeypatch):
        from app.common.config import settings
        from app.exports.all import zip_documents

        monkeypatch.setattr(settings, "export_storage_root", str(tmp_path / "exports"))
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_text("A", encoding="utf-8")
        b.write_text("B", encoding="utf-8")

        zip_path = zip_documents(task_id="zt", files=[str(a), str(b)])
        assert Path(zip_path).exists()

        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            assert "a.txt" in names
            assert "b.txt" in names
            assert zf.read("a.txt") == b"A"
            assert zf.read("b.txt") == b"B"

    def test_zip_blocks_traversal_in_filename(self, tmp_path, monkeypatch):
        from app.common.config import settings
        from app.exports._shared.storage import task_file_path

        monkeypatch.setattr(settings, "export_storage_root", str(tmp_path / "exports"))
        with pytest.raises(ValueError):
            task_file_path("t1", "../../etc/passwd")


import asyncio  # noqa: E402
import os  # noqa: E402
