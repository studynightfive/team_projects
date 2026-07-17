"""MIME / extension / magic-byte detection."""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path

from app.common.exceptions import AppException
from app.common.schemas import ErrorCode

try:
    import magic as python_magic
except Exception:  # pragma: no cover - optional native lib
    python_magic = None  # type: ignore[assignment]


# Extension -> expected MIME families
EXTENSION_MIME_MAP: dict[str, set[str]] = {
    ".pdf": {"application/pdf"},
    ".doc": {"application/msword", "application/octet-stream"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
        "application/octet-stream",
    },
    ".xls": {"application/vnd.ms-excel", "application/octet-stream"},
    ".xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/zip",
        "application/octet-stream",
    },
    ".ppt": {"application/vnd.ms-powerpoint", "application/octet-stream"},
    ".pptx": {
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/zip",
        "application/octet-stream",
    },
    ".md": {"text/markdown", "text/plain", "text/x-markdown"},
    ".markdown": {"text/markdown", "text/plain", "text/x-markdown"},
    ".txt": {"text/plain"},
    ".log": {"text/plain"},
    ".rst": {"text/plain", "text/x-rst"},
    ".org": {"text/plain"},
    ".csv": {"text/csv", "text/plain", "application/csv"},
    ".tsv": {"text/tab-separated-values", "text/plain"},
    ".html": {"text/html"},
    ".htm": {"text/html"},
    ".xml": {"application/xml", "text/xml"},
    ".json": {"application/json", "text/plain", "text/json"},
    ".epub": {"application/epub+zip", "application/zip"},
    ".odt": {"application/vnd.oasis.opendocument.text", "application/zip"},
    ".ods": {"application/vnd.oasis.opendocument.spreadsheet", "application/zip"},
    ".odp": {"application/vnd.oasis.opendocument.presentation", "application/zip"},
    ".rtf": {"application/rtf", "text/rtf"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
    ".webp": {"image/webp"},
    ".bmp": {"image/bmp", "image/x-ms-bmp"},
    ".tif": {"image/tiff"},
    ".tiff": {"image/tiff"},
    ".eml": {"message/rfc822", "text/plain"},
}

SIGNATURES: list[tuple[bytes, str]] = [
    (b"%PDF", "application/pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"BM", "image/bmp"),
    (b"RIFF", "image/webp"),  # refined below
    (b"PK\x03\x04", "application/zip"),
    (b"{\\", "application/rtf"),
]


@dataclass
class DetectedFile:
    extension: str
    declared_mime: str
    detected_mime: str
    filename: str


def _detect_by_signature(data: bytes) -> str | None:
    for sig, mime in SIGNATURES:
        if data.startswith(sig):
            if mime == "image/webp" and b"WEBP" not in data[:16]:
                continue
            return mime
    if data.lstrip().startswith((b"{", b"[")):
        return "application/json"
    if data.lstrip().startswith((b"<!DOCTYPE", b"<html", b"<HTML", b"<?xml")):
        lower = data[:200].lower()
        if b"<html" in lower or b"<!doctype html" in lower:
            return "text/html"
        if b"<?xml" in lower or b"<xml" in lower:
            return "application/xml"
    textish = True
    sample = data[:4096]
    if not sample:
        return "application/octet-stream"
    for b in sample:
        if b == 0:
            textish = False
            break
    if textish:
        return "text/plain"
    return None


def detect_mime(data: bytes, filename: str) -> str:
    if python_magic is not None:
        try:
            mime = python_magic.from_buffer(data, mime=True)
            if mime:
                return str(mime)
        except Exception:
            pass
    by_sig = _detect_by_signature(data)
    if by_sig:
        return by_sig
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


def detect_file(filename: str, data: bytes) -> DetectedFile:
    from app.documents.storage import sanitize_filename

    safe = sanitize_filename(filename)
    extension = Path(safe).suffix.lower()
    declared = mimetypes.guess_type(safe)[0] or "application/octet-stream"
    detected = detect_mime(data, safe)

    allowed = EXTENSION_MIME_MAP.get(extension)
    if allowed is None:
        # Unknown extension — keep original, route to manual review later
        return DetectedFile(extension=extension or ".bin", declared_mime=declared, detected_mime=detected, filename=safe)

    if detected not in allowed and not (
        detected.startswith("text/") and any(a.startswith("text/") for a in allowed)
    ):
        # ZIP containers for OOXML are acceptable when extension matches
        if not (detected == "application/zip" and extension in {".docx", ".xlsx", ".pptx", ".odt", ".ods", ".odp", ".epub"}):
            raise AppException(
                code=ErrorCode.UPLOAD_MIME_MISMATCH,
                message=f"文件头与扩展名不一致: ext={extension}, mime={detected}",
                status_code=400,
            )
    return DetectedFile(extension=extension, declared_mime=declared, detected_mime=detected, filename=safe)
