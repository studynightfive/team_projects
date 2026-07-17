"""Markdown normalization, sanitization and package generation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import bleach

from app.parsers.base import ParsedAsset, ParsedDocument

ALLOWED_TAGS = [
    "p",
    "br",
    "hr",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "ul",
    "ol",
    "li",
    "strong",
    "em",
    "code",
    "pre",
    "blockquote",
    "a",
    "img",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "span",
    "div",
]
ALLOWED_ATTRS = {
    "a": ["href", "title", "rel", "target"],
    "img": ["src", "alt", "title"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan"],
    "*": ["class", "id"],
}
ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


@dataclass
class MarkdownPackage:
    title: str
    content_md: str
    assets: list[tuple[str, bytes, str, int | None]] = field(default_factory=list)
    # filename, data, mime, page_no
    manifest: dict[str, Any] = field(default_factory=dict)


def sanitize_markdown_html(text: str) -> str:
    cleaned = bleach.clean(
        text,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    # Remove javascript: and data: leftovers that may survive attribute filters
    cleaned = re.sub(r"javascript:", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"data:text/html", "", cleaned, flags=re.IGNORECASE)
    return cleaned


def _escape_md(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


class MarkdownConverter:
    async def convert(
        self,
        parsed: ParsedDocument,
        *,
        content_hash: str,
        original_filename: str,
    ) -> MarkdownPackage:
        lines: list[str] = [f"# {parsed.title.strip() or 'Untitled'}", ""]
        page_anchors: set[int] = set()
        assets_meta: list[dict[str, Any]] = []
        asset_tuples: list[tuple[str, bytes, str, int | None]] = []

        for idx, asset in enumerate(parsed.assets, start=1):
            name = asset.filename or f"image-{idx:03d}.bin"
            safe_name = re.sub(r"[^\w.\-]+", "_", name)
            if not safe_name:
                safe_name = f"image-{idx:03d}.png"
            asset_tuples.append((safe_name, asset.data, asset.mime_type, asset.page_no))
            assets_meta.append(
                {
                    "filename": safe_name,
                    "mime_type": asset.mime_type,
                    "page_no": asset.page_no,
                    "description": asset.description,
                }
            )

        asset_iter = iter(asset_tuples)
        skipped_title_heading = False
        for block in parsed.blocks:
            if block.page_no and block.page_no not in page_anchors:
                lines.append(f'<a id="page-{block.page_no}"></a>')
                lines.append(f"<!-- page:{block.page_no} -->")
                lines.append("")
                page_anchors.add(block.page_no)

            if block.block_type == "meta":
                continue
            # Document title uses H1; demote original H1 body headings to H2+.
            if block.block_type == "heading":
                if (
                    not skipped_title_heading
                    and (block.level or 1) == 1
                    and block.text.strip() == parsed.title.strip()
                ):
                    skipped_title_heading = True
                    continue
                level = block.level or 2
                if level == 1:
                    level = 2
                else:
                    level = min(max(level, 2), 6)
                lines.append(f"{'#' * level} {_escape_md(block.text)}")
                lines.append("")
            elif block.block_type == "table":
                lines.append(sanitize_markdown_html(block.text))
                lines.append("")
            elif block.block_type == "code":
                lines.append("```")
                lines.append(_escape_md(block.text))
                lines.append("```")
                lines.append("")
            elif block.block_type == "image":
                try:
                    name, _, _, _ = next(asset_iter)
                except StopIteration:
                    name = "missing.png"
                alt = block.text or name
                lines.append(f"![{alt}](../assets/{name})")
                if block.confidence is not None:
                    lines.append(f"<!-- ocr_confidence:{block.confidence:.3f} -->")
                lines.append("")
            else:
                text = sanitize_markdown_html(_escape_md(block.text))
                lines.append(text)
                meta_bits = []
                if block.confidence is not None:
                    meta_bits.append(f"ocr_confidence:{block.confidence:.3f}")
                if block.sheet_name:
                    meta_bits.append(f"sheet:{block.sheet_name}")
                if block.slide_no:
                    meta_bits.append(f"slide:{block.slide_no}")
                if meta_bits:
                    lines.append(f"<!-- {' '.join(meta_bits)} -->")
                lines.append("")

        # Ensure remaining assets are referenced
        remaining = list(asset_iter)
        for name, _, _, page_no in remaining:
            if page_no and page_no not in page_anchors:
                lines.append(f'<a id="page-{page_no}"></a>')
                page_anchors.add(page_no)
            lines.append(f"![{name}](../assets/{name})")
            lines.append("")

        content = "\n".join(lines).strip() + "\n"
        content = sanitize_markdown_html(content)

        # Re-assert title as H1 after sanitize (bleach may leave anchors)
        if not content.lstrip().startswith("# "):
            content = f"# {parsed.title}\n\n{content}"

        manifest = {
            "title": parsed.title,
            "original_filename": original_filename,
            "content_hash": content_hash,
            "parser_name": parsed.parser_name,
            "parser_version": parsed.parser_version,
            "converted_at": datetime.now(timezone.utc).isoformat(),
            "page_count": parsed.page_count,
            "pages": sorted(page_anchors),
            "assets": assets_meta,
            "warnings": parsed.warnings,
            "source_metadata": parsed.source_metadata,
        }
        return MarkdownPackage(
            title=parsed.title,
            content_md=content,
            assets=[(n, d, m, p) for n, d, m, p in asset_tuples],
            manifest=manifest,
        )


# Keep ParsedAsset import used for typing clarity in public API
__all__ = ["MarkdownConverter", "MarkdownPackage", "sanitize_markdown_html", "ParsedAsset"]
