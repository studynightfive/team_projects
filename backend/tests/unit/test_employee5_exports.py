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
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

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

    @pytest.mark.parametrize("prefix", ["=", "+", "-", "@", "\t", "\r"])
    def test_formula_prefix_is_escaped(self, tmp_path, monkeypatch, prefix):
        import csv as csvmod

        from app.common.config import settings
        from app.exports._shared.storage import task_file_path
        from app.exports.all import CsvExporter, ExportContent, ExportOptions

        monkeypatch.setattr(settings, "export_storage_root", str(tmp_path / "exports"))
        content = ExportContent(
            document_id="d1",
            title=f"{prefix}danger",
            markdown=f"{prefix}payload",
        )
        out = task_file_path("t1", "formula.csv")
        result = asyncio.run(CsvExporter().export(content, out, ExportOptions()))
        with open(result, encoding="utf-8", newline="") as file:
            rows = list(csvmod.reader(file))
        assert rows[1][1].startswith("'")
        assert rows[2][1].startswith("'")


class TestPdfResourceBoundary:
    def test_network_resource_is_rejected(self):
        from app.exports.all import _local_asset_url_fetcher

        with pytest.raises(ValueError, match="禁止访问网络"):
            _local_asset_url_fetcher("https://example.com/tracker.png")

    def test_file_outside_storage_is_rejected(self, tmp_path, monkeypatch):
        from app.common.config import settings
        from app.exports.all import _local_asset_url_fetcher

        storage = tmp_path / "exports"
        outside = tmp_path / "outside.png"
        storage.mkdir()
        outside.write_bytes(b"not-an-image")
        monkeypatch.setattr(settings, "export_storage_root", str(storage))
        with pytest.raises(ValueError, match="受控存储目录"):
            _local_asset_url_fetcher(outside.resolve().as_uri())


class TestExportCleanup:
    @pytest.mark.asyncio
    async def test_only_expired_terminal_tasks_are_cleaned(self, monkeypatch):
        from sqlalchemy.dialects import postgresql

        from app.exports import all as exports

        done = SimpleNamespace(id="done-task", status="done")
        pending = SimpleNamespace(id="pending-task", status="pending")
        result = MagicMock()
        result.scalars.return_value.all.return_value = [done, pending]
        db = AsyncMock()
        db.execute.return_value = result
        deleted: list[str] = []
        monkeypatch.setattr(exports, "delete_task_dir", deleted.append)

        count = await exports.cleanup_expired(db)

        statement = db.execute.await_args.args[0]
        sql = str(
            statement.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )
        assert "export_tasks.status IN ('done', 'failed', 'cancelled')" in sql
        assert "FOR UPDATE SKIP LOCKED" in sql
        assert count == 1
        assert deleted == ["done-task"]
        assert done.status == "expired"
        assert pending.status == "pending"
        db.commit.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_delete_failure_keeps_task_retryable_and_continues(self, monkeypatch):
        from app.exports import all as exports

        blocked = SimpleNamespace(id="blocked-task", status="failed")
        removable = SimpleNamespace(id="removable-task", status="cancelled")
        result = MagicMock()
        result.scalars.return_value.all.return_value = [blocked, removable]
        db = AsyncMock()
        db.execute.return_value = result

        def delete_task_dir(task_id: str) -> None:
            if task_id == "blocked-task":
                raise OSError("locked")

        monkeypatch.setattr(exports, "delete_task_dir", delete_task_dir)

        count = await exports.cleanup_expired(db)

        assert count == 1
        assert blocked.status == "failed"
        assert removable.status == "expired"
        db.commit.assert_awaited_once_with()


class TestDownloadPathBoundary:
    def test_file_inside_current_task_directory_is_allowed(self, tmp_path, monkeypatch):
        from app.common.config import settings
        from app.exports.all import _resolve_download_path

        storage = tmp_path / "exports"
        task_storage = storage / "task-1"
        task_storage.mkdir(parents=True)
        exported = task_storage / "report.pdf"
        exported.write_bytes(b"pdf")
        monkeypatch.setattr(settings, "export_storage_root", str(storage))

        resolved = _resolve_download_path(
            SimpleNamespace(id="task-1", file_path=str(exported))
        )

        assert resolved == exported.resolve()

    @pytest.mark.parametrize("target_kind", ["outside", "directory"])
    def test_non_task_file_is_rejected(self, tmp_path, monkeypatch, target_kind):
        from app.common.config import settings
        from app.common.exceptions import NotFoundException
        from app.exports.all import _resolve_download_path

        storage = tmp_path / "exports"
        task_storage = storage / "task-1"
        task_storage.mkdir(parents=True)
        outside = storage / "outside.pdf"
        outside.write_bytes(b"pdf")
        monkeypatch.setattr(settings, "export_storage_root", str(storage))
        target = outside if target_kind == "outside" else task_storage

        with pytest.raises(NotFoundException):
            _resolve_download_path(SimpleNamespace(id="task-1", file_path=str(target)))


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


class TestAnswerExportTask:
    @pytest.mark.parametrize(
        ("export_format", "extension"),
        [("pdf", ".pdf"), ("docx", ".docx"), ("markdown", ".md")],
    )
    @pytest.mark.asyncio
    async def test_answer_export_persists_downloadable_task(
        self,
        tmp_path,
        monkeypatch,
        export_format,
        extension,
    ):
        from datetime import datetime, timezone

        from starlette.requests import Request

        from app.common.config import settings
        from app.exports import all as exports

        added_tasks = []

        def add_task(task):
            task.id = "answer-task-1"
            task.created_at = datetime.now(timezone.utc)
            added_tasks.append(task)

        db = SimpleNamespace(add=add_task, commit=AsyncMock())
        monkeypatch.setattr(settings, "export_storage_root", str(tmp_path / "exports"))
        monkeypatch.setattr(exports, "audit", AsyncMock())
        response = await exports.export_answer_endpoint(
            request=Request(
                {
                    "type": "http",
                    "method": "POST",
                    "path": "/api/v1/exports/answer",
                    "headers": [],
                }
            ),
            payload=exports.AnswerExportRequest(
                format=export_format,
                question="医院信息平台如何规划？",
                answer="应先完成数据标准和接口治理。",
                citations=[{"doc_id": "doc-1", "chunk_id": "chunk-1", "score": 0.9}],
            ),
            user=SimpleNamespace(id="user-1"),
            _perm=None,
            db=db,
        )

        task = added_tasks[0]
        exported = Path(response.path)
        assert task.user_id == "user-1"
        assert task.document_ids == []
        assert task.status == "done"
        assert task.progress == 100
        assert exported.suffix == extension
        assert exported.exists()
        assert exported.stat().st_size > 0
        assert response.headers["x-export-id"] == task.id
        assert db.commit.await_count >= 3

        record = exports._task_to_response(task)
        assert record.source_type == "answer"
        assert record.filename == exported.name
        assert record.download_url is not None

    @pytest.mark.asyncio
    async def test_answer_export_failure_keeps_failed_record(
        self,
        tmp_path,
        monkeypatch,
    ):
        from datetime import datetime, timezone

        from starlette.requests import Request

        from app.common.config import settings
        from app.common.exceptions import AppException
        from app.exports import all as exports

        class FailedExporter:
            format_name = "markdown"

            async def export(self, content, output_path, options):
                raise RuntimeError("renderer failed")

        added_tasks = []

        def add_task(task):
            task.id = "failed-answer-task"
            task.created_at = datetime.now(timezone.utc)
            added_tasks.append(task)

        db = SimpleNamespace(add=add_task, commit=AsyncMock())
        monkeypatch.setattr(settings, "export_storage_root", str(tmp_path / "exports"))
        monkeypatch.setitem(exports.EXPORTERS, "markdown", FailedExporter())

        with pytest.raises(AppException) as exc_info:
            await exports.export_answer_endpoint(
                request=Request(
                    {
                        "type": "http",
                        "method": "POST",
                        "path": "/api/v1/exports/answer",
                        "headers": [],
                    }
                ),
                payload=exports.AnswerExportRequest(
                    format="markdown",
                    question="问题",
                    answer="答案",
                ),
                user=SimpleNamespace(id="user-1"),
                _perm=None,
                db=db,
            )

        task = added_tasks[0]
        assert exc_info.value.status_code == 500
        assert task.status == "failed"
        assert task.error_code == "export_failed"
        assert not (tmp_path / "exports" / task.id).exists()
