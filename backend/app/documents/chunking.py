"""Markdown-aware chunking."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.common.config import Settings
from app.common.config import settings as app_settings
from app.common.exceptions import ValidationException


@dataclass
class Chunk:
    chunk_no: int
    content: str
    heading: str | None
    section_no: int | None
    page_no: int | None
    char_start: int
    char_end: int
    token_estimate: int


@dataclass
class _MarkdownUnit:
    text: str
    kind: str
    char_start: int
    char_end: int


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_PAGE_RE = re.compile(r"<!--\s*page:(\d+)\s*-->")
_PAGE_ANCHOR_RE = re.compile(r'<a id="page-(\d+)"></a>')


class Chunker:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings if settings is not None else app_settings

    def validate_params(self, chunk_size: int, overlap: int) -> tuple[int, int]:
        if chunk_size < self.settings.chunk_size_min or chunk_size > self.settings.chunk_size_max:
            raise ValidationException(
                f"chunk_size 必须在 {self.settings.chunk_size_min}-{self.settings.chunk_size_max}",
            )
        if overlap < self.settings.chunk_overlap_min or overlap >= chunk_size:
            raise ValidationException("chunk_overlap 非法")
        return chunk_size, overlap

    async def split(
        self,
        markdown: str,
        metadata: dict[str, int] | None = None,
        *,
        chunk_size: int | None = None,
        overlap: int | None = None,
    ) -> list[Chunk]:
        metadata = metadata or {}
        size = chunk_size or int(metadata.get("chunk_size") or self.settings.chunk_size_default)
        ov = (
            overlap
            if overlap is not None
            else int(metadata.get("chunk_overlap") or self.settings.chunk_overlap_default)
        )
        size, ov = self.validate_params(size, ov)

        normalized_markdown = markdown.replace("\r\n", "\n")
        units = self._split_units(normalized_markdown)
        chunks: list[Chunk] = []
        current_heading: str | None = None
        current_heading_text: str | None = None
        current_section = 0
        current_page: int | None = None

        def append_chunk(
            content: str,
            *,
            heading: str | None,
            section_no: int | None,
            page_no: int | None,
            char_start: int,
            char_end: int,
        ) -> None:
            text = content.strip()
            if not text:
                return
            chunks.append(
                Chunk(
                    chunk_no=len(chunks) + 1,
                    content=text,
                    heading=heading,
                    section_no=section_no,
                    page_no=page_no,
                    char_start=char_start,
                    char_end=char_end,
                    token_estimate=max(1, len(text) // 4),
                )
            )

        def append_semantic_unit(unit: _MarkdownUnit) -> None:
            prefix = (
                f"{current_heading_text}\n\n"
                if current_heading_text is not None and unit.kind != "heading"
                else ""
            )
            content = f"{prefix}{unit.text}"
            if len(content) <= size or unit.kind in {"table", "code"}:
                append_chunk(
                    content,
                    heading=current_heading,
                    section_no=current_section or None,
                    page_no=current_page,
                    char_start=unit.char_start,
                    char_end=unit.char_end,
                )
                return

            body_limit = max(1, size - len(prefix))
            step = max(1, body_limit - ov)
            offset = 0
            while offset < len(unit.text):
                part = unit.text[offset : offset + body_limit].strip()
                if part:
                    append_chunk(
                        f"{prefix}{part}",
                        heading=current_heading,
                        section_no=current_section or None,
                        page_no=current_page,
                        char_start=unit.char_start + offset,
                        char_end=min(unit.char_start + offset + len(part), unit.char_end),
                    )
                offset += step

        for unit in units:
            page_match = _PAGE_RE.search(unit.text) or _PAGE_ANCHOR_RE.search(unit.text)
            if page_match:
                current_page = int(page_match.group(1))
                if unit.kind == "page":
                    continue

            heading_match = _HEADING_RE.match(unit.text.strip())
            if heading_match:
                current_section += 1
                current_heading = heading_match.group(2).strip()
                current_heading_text = unit.text.strip()
                append_semantic_unit(unit)
                continue

            append_semantic_unit(unit)

        if not chunks and normalized_markdown.strip():
            chunks.append(
                Chunk(
                    chunk_no=1,
                    content=normalized_markdown.strip(),
                    heading=None,
                    section_no=None,
                    page_no=None,
                    char_start=0,
                    char_end=len(normalized_markdown.strip()),
                    token_estimate=max(1, len(normalized_markdown.strip()) // 4),
                )
            )
        return chunks

    def _split_units(self, markdown: str) -> list[_MarkdownUnit]:
        unit_texts = self._split_unit_texts(markdown)
        units: list[_MarkdownUnit] = []
        cursor = 0
        for text in unit_texts:
            start = markdown.find(text, cursor)
            if start < 0:
                start = cursor
            end = start + len(text)
            units.append(
                _MarkdownUnit(
                    text=text,
                    kind=self._classify_unit(text),
                    char_start=start,
                    char_end=end,
                )
            )
            cursor = end
        return units

    def _split_unit_texts(self, markdown: str) -> list[str]:
        lines = markdown.replace("\r\n", "\n").split("\n")
        units: list[str] = []
        buf: list[str] = []
        in_code = False
        in_table = False

        def push_buf() -> None:
            nonlocal buf
            text = "\n".join(buf).strip("\n")
            if text.strip():
                units.append(text)
            buf = []

        for line in lines:
            if line.strip().startswith("```"):
                if not in_code:
                    push_buf()
                    in_code = True
                    buf = [line]
                else:
                    buf.append(line)
                    push_buf()
                    in_code = False
                continue
            if in_code:
                buf.append(line)
                continue

            if line.strip().startswith("|"):
                if not in_table:
                    push_buf()
                    in_table = True
                buf.append(line)
                continue
            if in_table:
                push_buf()
                in_table = False

            if _HEADING_RE.match(line) or _PAGE_RE.search(line) or _PAGE_ANCHOR_RE.search(line):
                push_buf()
                units.append(line)
                continue

            if not line.strip():
                push_buf()
                continue
            buf.append(line)

        if in_table or in_code or buf:
            push_buf()
        return units

    def _classify_unit(self, text: str) -> str:
        stripped = text.strip()
        if _HEADING_RE.match(stripped):
            return "heading"
        if _PAGE_RE.search(stripped) or _PAGE_ANCHOR_RE.search(stripped):
            return "page"
        if stripped.startswith("```"):
            return "code"
        if stripped.startswith("|"):
            return "table"
        return "paragraph"
