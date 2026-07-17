"""Image OCR with optional Tesseract and preprocessing."""

from __future__ import annotations

import asyncio
import shutil
import tempfile
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

from app.common.config import settings as get_settings_obj

def get_settings():
    return get_settings_obj
from app.parsers.base import DocumentParser, ParsedAsset, ParsedBlock, ParsedDocument


def preprocess_image_bytes(data: bytes) -> bytes:
    image = Image.open(BytesIO(data))
    image = ImageOps.exif_transpose(image)
    image = image.convert("L")
    image = ImageOps.autocontrast(image)
    image = image.filter(ImageFilter.MedianFilter(size=3))
    # Upscale small images for better OCR
    if min(image.size) < 800:
        scale = 800 / min(image.size)
        image = image.resize((int(image.width * scale), int(image.height * scale)), Image.Resampling.LANCZOS)
    out = BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


async def ocr_image_bytes(data: bytes, *, language: str | None = None) -> tuple[str, float]:
    settings = get_settings()
    lang = language or settings.ocr_default_languages
    tesseract = shutil.which(settings.tesseract_bin)
    if not tesseract:
        # Deterministic fallback for environments without Tesseract:
        # expose placeholder so pipeline continues; tests can monkeypatch.
        return "", 0.0

    with tempfile.TemporaryDirectory(prefix="ocr-") as tmp:
        src = Path(tmp) / "input.png"
        src.write_bytes(data)
        out_base = Path(tmp) / "out"
        cmd = [
            tesseract,
            str(src),
            str(out_base),
            "-l",
            lang,
            "--psm",
            "3",
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            await asyncio.wait_for(proc.communicate(), timeout=settings.tesseract_timeout_seconds)
        except asyncio.TimeoutError:
            proc.kill()
            return "", 0.0
        text_path = Path(str(out_base) + ".txt")
        if not text_path.exists():
            return "", 0.0
        text = text_path.read_text(encoding="utf-8", errors="replace").strip()
        # Tesseract CLI without TSV does not return confidence; estimate by length heuristic.
        confidence = 0.75 if text else 0.0
        return text, confidence


class ImageParser(DocumentParser):
    name = "image_ocr"

    def supports(self, mime_type: str, extension: str) -> bool:
        return extension in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"} or mime_type.startswith(
            "image/"
        )

    async def parse(self, source_path: str) -> ParsedDocument:
        path = Path(source_path)
        raw = path.read_bytes()
        processed = preprocess_image_bytes(raw)
        # language is applied later by pipeline via enrich; default here
        text, confidence = await ocr_image_bytes(processed)
        blocks: list[ParsedBlock] = [
            ParsedBlock(text="<!-- page:1 -->", block_type="meta", page_no=1),
        ]
        warnings: list[str] = []
        if text:
            blocks.append(
                ParsedBlock(
                    text=text,
                    block_type="paragraph",
                    page_no=1,
                    confidence=confidence,
                    metadata={"source": "ocr"},
                )
            )
        else:
            warnings.append("ocr_empty_or_tesseract_unavailable")
            blocks.append(
                ParsedBlock(
                    text="（图片已保存，OCR 未识别到文本）",
                    block_type="paragraph",
                    page_no=1,
                    confidence=0.0,
                )
            )
        asset_name = f"original{path.suffix.lower() or '.png'}"
        return ParsedDocument(
            title=path.stem,
            blocks=blocks,
            assets=[
                ParsedAsset(
                    filename=asset_name,
                    data=raw,
                    mime_type=f"image/{path.suffix.lstrip('.').lower() or 'png'}",
                    page_no=1,
                    description=path.stem,
                )
            ],
            page_count=1,
            parser_name=self.name,
            warnings=warnings,
            needs_ocr=False,
        )
