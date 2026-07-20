"""PDF parser with native text extraction and OCR fallback for scanned pages."""

from __future__ import annotations

import asyncio
import multiprocessing
import time
from collections.abc import Callable
from contextlib import suppress
from multiprocessing.connection import Connection
from multiprocessing.process import BaseProcess
from pathlib import Path
from typing import cast

from pypdf import PdfReader

from app.common.config import settings as app_settings
from app.parsers.base import DocumentParser, ParsedAsset, ParsedBlock, ParsedDocument
from app.parsers.image_ocr import ocr_image_bytes, preprocess_image_bytes

_PDF_PROCESS_STOP_TIMEOUT_SECONDS = 5.0
PdfWorker = Callable[[str, int, Connection], None]


class PdfParser(DocumentParser):
    name = "pdf"

    def supports(self, mime_type: str, extension: str) -> bool:
        return extension == ".pdf" or mime_type == "application/pdf"

    async def parse(self, source_path: str) -> ParsedDocument:
        return await _parse_pdf_in_process(
            source_path,
            max_pages=app_settings.pdf_max_pages,
            timeout_seconds=app_settings.pdf_parse_timeout_seconds,
        )


def _parse_pdf_sync(source_path: str, max_pages: int) -> ParsedDocument:
    path = Path(source_path)
    try:
        reader = PdfReader(str(path))
        page_count = len(reader.pages)
    except Exception as exc:  # noqa: BLE001
        return ParsedDocument(
            title=path.stem,
            blocks=[],
            parser_name="pdf",
            manual_review=True,
            warnings=[f"pdf_open_failed:{type(exc).__name__}"],
        )

    if page_count > max_pages:
        return ParsedDocument(
            title=path.stem,
            blocks=[],
            page_count=page_count,
            parser_name="pdf",
            manual_review=True,
            warnings=["pdf_page_limit_exceeded"],
        )

    if getattr(reader, "is_encrypted", False):
        try:
            reader.decrypt("")
        except Exception:
            return ParsedDocument(
                title=path.stem,
                blocks=[],
                page_count=page_count,
                parser_name="pdf",
                manual_review=True,
                warnings=["encrypted_pdf"],
            )

    blocks: list[ParsedBlock] = []
    assets: list[ParsedAsset] = []
    empty_pages = 0
    for page_no, page in enumerate(reader.pages, start=1):
        try:
            text = (page.extract_text() or "").strip()
        except Exception as exc:  # noqa: BLE001
            blocks.append(
                ParsedBlock(
                    text="",
                    block_type="paragraph",
                    page_no=page_no,
                    metadata={"error_type": type(exc).__name__},
                )
            )
            empty_pages += 1
            continue
        blocks.append(
            ParsedBlock(
                text=f"<!-- page:{page_no} -->",
                block_type="meta",
                page_no=page_no,
            )
        )
        if text:
            for para in text.split("\n\n"):
                para = para.strip()
                if para:
                    blocks.append(
                        ParsedBlock(text=para, block_type="paragraph", page_no=page_no)
                    )
        else:
            empty_pages += 1

        try:
            resources = page.get("/Resources")
            if resources and "/XObject" in resources:
                xobject = resources["/XObject"].get_object()
                for img_name in xobject:
                    obj = xobject[img_name]
                    if obj.get("/Subtype") == "/Image":
                        assets.append(
                            ParsedAsset(
                                filename=f"page-{page_no}-{img_name[1:]}.bin",
                                data=obj.get_data(),
                                mime_type="application/octet-stream",
                                page_no=page_no,
                            )
                        )
        except Exception:
            pass

    needs_ocr = empty_pages >= max(1, page_count // 2)
    return ParsedDocument(
        title=path.stem,
        blocks=blocks,
        assets=assets,
        page_count=page_count,
        parser_name="pdf",
        needs_ocr=needs_ocr,
        warnings=["likely_scanned_pdf"] if needs_ocr else [],
    )


def _pdf_worker(source_path: str, max_pages: int, result_conn: Connection) -> None:
    _limit_pdf_worker_memory()
    try:
        result = _parse_pdf_sync(source_path, max_pages)
    except Exception:  # noqa: BLE001
        result = ParsedDocument(
            title=Path(source_path).stem,
            blocks=[],
            parser_name="pdf",
            manual_review=True,
            warnings=["pdf_parse_failed"],
        )
    try:
        result_conn.send(result)
    except (BrokenPipeError, EOFError, OSError):
        pass
    finally:
        result_conn.close()


def _limit_pdf_worker_memory() -> None:
    """在支持 RLIMIT_AS 的生产 Linux 子进程内限制畸形 PDF 的内存占用。"""
    try:
        import resource

        limit = app_settings.pdf_parse_memory_limit_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    except (ImportError, OSError, ValueError):
        # Windows 开发环境没有 resource；生产 Worker 运行于 Linux 容器。
        return


def _finish_pdf_process(process: BaseProcess, *, terminate: bool) -> None:
    if terminate and process.is_alive():
        with suppress(OSError):
            process.terminate()
    process.join(_PDF_PROCESS_STOP_TIMEOUT_SECONDS)
    if process.is_alive():
        with suppress(OSError):
            process.kill()
        process.join(_PDF_PROCESS_STOP_TIMEOUT_SECONDS)
    if not process.is_alive():
        process.close()


def _pdf_failure(source_path: str, warning: str) -> ParsedDocument:
    return ParsedDocument(
        title=Path(source_path).stem,
        blocks=[],
        parser_name="pdf",
        manual_review=True,
        warnings=[warning],
    )


async def _parse_pdf_in_process(
    source_path: str,
    *,
    max_pages: int,
    timeout_seconds: float,
    worker: PdfWorker = _pdf_worker,
) -> ParsedDocument:
    context = multiprocessing.get_context("spawn")
    parent_conn, child_conn = context.Pipe(duplex=False)
    process = context.Process(
        target=worker,
        args=(source_path, max_pages, child_conn),
        name="pdf-parser",
        daemon=True,
    )
    started = False
    terminate = False
    started_at = time.monotonic()
    try:
        process.start()
        started = True
        child_conn.close()
        ready = await asyncio.to_thread(parent_conn.poll, timeout_seconds)
        remaining = timeout_seconds - (time.monotonic() - started_at)
        if not ready or remaining <= 0:
            terminate = True
            return _pdf_failure(source_path, "pdf_parse_timeout")
        try:
            payload = cast(
                object,
                await asyncio.wait_for(
                    asyncio.to_thread(parent_conn.recv), timeout=remaining
                ),
            )
        except asyncio.TimeoutError:
            terminate = True
            return _pdf_failure(source_path, "pdf_parse_timeout")
        except (EOFError, OSError):
            terminate = True
            return _pdf_failure(source_path, "pdf_parse_failed")
        if isinstance(payload, ParsedDocument):
            return payload
        terminate = True
        return _pdf_failure(source_path, "pdf_parse_failed")
    except asyncio.CancelledError:
        terminate = True
        raise
    except Exception:  # noqa: BLE001
        terminate = True
        return _pdf_failure(source_path, "pdf_parse_failed")
    finally:
        parent_conn.close()
        child_conn.close()
        if started:
            await asyncio.to_thread(_finish_pdf_process, process, terminate=terminate)
        else:
            with suppress(ValueError):
                process.close()


async def enrich_pdf_with_ocr(
    parsed: ParsedDocument,
    source_path: str,
    *,
    language: str,
) -> ParsedDocument:
    """Best-effort OCR for scanned PDFs using page render or embedded images.

    Without Poppler, we OCR extracted image bytes and attach confidence metadata.
    """
    if not parsed.needs_ocr and parsed.blocks:
        text_blocks = [b for b in parsed.blocks if b.block_type == "paragraph" and b.text.strip()]
        if text_blocks:
            return parsed

    ocr_blocks: list[ParsedBlock] = []
    warnings = list(parsed.warnings)
    if parsed.assets:
        for asset in parsed.assets:
            try:
                processed = preprocess_image_bytes(asset.data)
                text, confidence = await ocr_image_bytes(processed, language=language)
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"ocr_asset_failed:{type(exc).__name__}")
                continue
            if text.strip():
                ocr_blocks.append(
                    ParsedBlock(
                        text=text.strip(),
                        block_type="paragraph",
                        page_no=asset.page_no,
                        confidence=confidence,
                        metadata={"source": "ocr"},
                    )
                )
    else:
        # Fallback: treat whole file as non-OCR-able without poppler; keep manual review flag soft
        warnings.append("ocr_no_page_images_available")

    if ocr_blocks:
        parsed.blocks = ocr_blocks
        parsed.needs_ocr = False
    else:
        parsed.warnings = warnings
    return parsed
