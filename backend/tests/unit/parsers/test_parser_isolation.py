"""Resource-isolation regression tests for untrusted Office and PDF inputs."""

from __future__ import annotations

import asyncio
import multiprocessing
import time
from pathlib import Path

import pytest

from app.common.exceptions import AppException
from app.parsers import office, pdf
from app.parsers.base import ParsedBlock, ParsedDocument


class _FakeLibreOfficeProcess:
    def __init__(self, *, returncode: int, stderr: bytes = b"", hangs: bool = False) -> None:
        self.pid = 12345
        self.returncode: int | None = None
        self._final_returncode = returncode
        self._stderr = stderr
        self._hangs = hangs
        self.communicate_calls = 0
        self.killed = False

    async def communicate(self) -> tuple[bytes, bytes]:
        self.communicate_calls += 1
        if self._hangs and self.communicate_calls == 1:
            await asyncio.Event().wait()
        if self.returncode is None:
            self.returncode = self._final_returncode
        return b"", self._stderr

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9

    async def wait(self) -> int:
        if self.returncode is None:
            self.returncode = self._final_returncode
        return self.returncode


def _install_fake_libreoffice(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    process: _FakeLibreOfficeProcess,
    *,
    create_output: bool,
) -> None:
    monkeypatch.setattr(office.tempfile, "tempdir", str(tmp_path))
    monkeypatch.setattr(office.shutil, "which", lambda _name: "soffice")

    async def fake_start(*cmd: str) -> _FakeLibreOfficeProcess:
        if create_output:
            out_dir = Path(cmd[cmd.index("--outdir") + 1])
            target_ext = cmd[cmd.index("--convert-to") + 1]
            (out_dir / f"converted.{target_ext}").write_bytes(b"converted")
        return process

    monkeypatch.setattr(office, "_start_libreoffice", fake_start)


@pytest.mark.asyncio
async def test_libreoffice_success_cleans_temporary_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    process = _FakeLibreOfficeProcess(returncode=0)
    _install_fake_libreoffice(monkeypatch, tmp_path, process, create_output=True)

    async with office.convert_with_libreoffice(tmp_path / "input.doc", "docx") as output:
        assert output.exists()

    assert list(tmp_path.glob("lo-convert-*")) == []


@pytest.mark.asyncio
async def test_libreoffice_failure_is_sanitized_and_cleans_temporary_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    process = _FakeLibreOfficeProcess(
        returncode=1,
        stderr=b"failed to open C:/private/internal/customer.doc",
    )
    _install_fake_libreoffice(monkeypatch, tmp_path, process, create_output=False)

    with pytest.raises(AppException) as exc_info:
        async with office.convert_with_libreoffice(tmp_path / "input.doc", "docx"):
            pass

    assert exc_info.value.message == "LibreOffice 转换失败"
    assert "private" not in exc_info.value.message
    assert list(tmp_path.glob("lo-convert-*")) == []


@pytest.mark.asyncio
async def test_libreoffice_timeout_reaps_process_and_cleans_temporary_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    process = _FakeLibreOfficeProcess(returncode=0, hangs=True)
    _install_fake_libreoffice(monkeypatch, tmp_path, process, create_output=False)
    monkeypatch.setattr(office.app_settings, "libreoffice_timeout_seconds", 0.01)

    async def fake_kill_tree(proc: _FakeLibreOfficeProcess) -> None:
        proc.kill()

    monkeypatch.setattr(office, "_kill_libreoffice_tree", fake_kill_tree)

    with pytest.raises(AppException) as exc_info:
        async with office.convert_with_libreoffice(tmp_path / "input.doc", "docx"):
            pass

    assert exc_info.value.message == "LibreOffice 转换超时"
    assert process.killed
    assert process.communicate_calls == 2
    assert list(tmp_path.glob("lo-convert-*")) == []


class _TooManyPagesReader:
    is_encrypted = False
    pages = [object(), object()]

    def __init__(self, _source_path: str) -> None:
        pass


def test_pdf_page_limit_stops_before_page_extraction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pdf, "PdfReader", _TooManyPagesReader)

    parsed = pdf._parse_pdf_sync("C:/private/internal.pdf", max_pages=1)

    assert parsed.manual_review
    assert parsed.page_count == 2
    assert parsed.warnings == ["pdf_page_limit_exceeded"]


def _slow_pdf_worker(_source_path: str, _max_pages: int, _result_conn: object) -> None:
    time.sleep(60)


def _successful_pdf_worker(source_path: str, _max_pages: int, result_conn: object) -> None:
    document = ParsedDocument(
        title=Path(source_path).stem,
        blocks=[ParsedBlock(text="ok")],
        parser_name="pdf",
    )
    result_conn.send(document)  # type: ignore[attr-defined]
    result_conn.close()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_pdf_timeout_does_not_block_loop_or_poison_following_task() -> None:
    children_before = {child.pid for child in multiprocessing.active_children()}
    slow_task = asyncio.create_task(
        pdf._parse_pdf_in_process(
            "slow.pdf",
            max_pages=10,
            timeout_seconds=0.3,
            worker=_slow_pdf_worker,
        )
    )

    await asyncio.sleep(0.03)
    assert not slow_task.done()
    timed_out = await slow_task
    assert timed_out.manual_review
    assert timed_out.warnings == ["pdf_parse_timeout"]

    succeeded = await pdf._parse_pdf_in_process(
        "next.pdf",
        max_pages=10,
        timeout_seconds=10,
        worker=_successful_pdf_worker,
    )
    assert succeeded.blocks[0].text == "ok"
    assert {child.pid for child in multiprocessing.active_children()} <= children_before
