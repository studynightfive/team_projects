"""PDF parser with native text extraction and OCR fallback for scanned pages."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from app.parsers.base import DocumentParser, ParsedAsset, ParsedBlock, ParsedDocument
from app.parsers.image_ocr import ocr_image_bytes, preprocess_image_bytes


class PdfParser(DocumentParser):
    name = "pdf"

    def supports(self, mime_type: str, extension: str) -> bool:
        return extension == ".pdf" or mime_type == "application/pdf"

    async def parse(self, source_path: str) -> ParsedDocument:
        path = Path(source_path)
        try:
            reader = PdfReader(str(path))
        except Exception as exc:  # noqa: BLE001
            return ParsedDocument(
                title=path.stem,
                blocks=[],
                parser_name=self.name,
                manual_review=True,
                warnings=[f"pdf_open_failed: {exc}"],
            )

        if getattr(reader, "is_encrypted", False):
            try:
                reader.decrypt("")
            except Exception:
                return ParsedDocument(
                    title=path.stem,
                    blocks=[],
                    parser_name=self.name,
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
                        metadata={"error": str(exc)},
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
                        blocks.append(ParsedBlock(text=para, block_type="paragraph", page_no=page_no))
            else:
                empty_pages += 1

            # Extract embedded images when present
            try:
                resources = page.get("/Resources")
                if resources and "/XObject" in resources:
                    xobject = resources["/XObject"].get_object()
                    for img_name in xobject:
                        obj = xobject[img_name]
                        if obj.get("/Subtype") == "/Image":
                            data = obj.get_data()
                            assets.append(
                                ParsedAsset(
                                    filename=f"page-{page_no}-{img_name[1:]}.bin",
                                    data=data,
                                    mime_type="application/octet-stream",
                                    page_no=page_no,
                                )
                            )
            except Exception:
                pass

        needs_ocr = empty_pages >= max(1, len(reader.pages) // 2)
        return ParsedDocument(
            title=path.stem,
            blocks=blocks,
            assets=assets,
            page_count=len(reader.pages),
            parser_name=self.name,
            needs_ocr=needs_ocr,
            warnings=["likely_scanned_pdf"] if needs_ocr else [],
        )


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
                warnings.append(f"ocr_asset_failed:{exc}")
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
