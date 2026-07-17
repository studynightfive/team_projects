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
        metadata: dict | None = None,
        *,
        chunk_size: int | None = None,
        overlap: int | None = None,
    ) -> list[Chunk]:
        metadata = metadata or {}
        size = chunk_size or int(metadata.get("chunk_size") or self.settings.chunk_size_default)
        ov = overlap if overlap is not None else int(
            metadata.get("chunk_overlap") or self.settings.chunk_overlap_default
        )
        size, ov = self.validate_params(size, ov)

        units = self._split_units(markdown)
        chunks: list[Chunk] = []
        buf: list[str] = []
        buf_len = 0
        current_heading: str | None = None
        current_section = 0
        current_page: int | None = None
        cursor = 0

        def flush() -> None:
            nonlocal buf, buf_len, cursor
            if not buf:
                return
            content = "\n\n".join(buf).strip()
            if not content:
                buf, buf_len = [], 0
                return
            start = cursor
            end = start + len(content)
            chunks.append(
                Chunk(
                    chunk_no=len(chunks) + 1,
                    content=content,
                    heading=current_heading,
                    section_no=current_section or None,
                    page_no=current_page,
                    char_start=start,
                    char_end=end,
                    token_estimate=max(1, len(content) // 4),
                )
            )
            cursor = end + 2
            if ov > 0 and content:
                overlap_text = content[-ov:]
                buf = [overlap_text]
                buf_len = len(overlap_text)
            else:
                buf, buf_len = [], 0

        for unit in units:
            page_match = _PAGE_RE.search(unit) or _PAGE_ANCHOR_RE.search(unit)
            if page_match:
                current_page = int(page_match.group(1))

            heading_match = _HEADING_RE.match(unit.strip())
            if heading_match:
                # Prefer boundary flush before new heading
                if buf:
                    flush()
                current_section += 1
                current_heading = heading_match.group(2).strip()

            # Keep tables/code intact: if unit alone exceeds size, emit as single chunk
            unit_len = len(unit)
            if unit_len > size and (unit.strip().startswith("|") or unit.strip().startswith("```")):
                if buf:
                    flush()
                buf = [unit]
                buf_len = unit_len
                flush()
                continue

            if buf_len + unit_len + (2 if buf else 0) > size and buf:
                flush()
            buf.append(unit)
            buf_len += unit_len + (2 if len(buf) > 1 else 0)

        flush()
        if not chunks and markdown.strip():
            chunks.append(
                Chunk(
                    chunk_no=1,
                    content=markdown.strip(),
                    heading=None,
                    section_no=None,
                    page_no=None,
                    char_start=0,
                    char_end=len(markdown.strip()),
                    token_estimate=max(1, len(markdown.strip()) // 4),
                )
            )
        return chunks

    def _split_units(self, markdown: str) -> list[str]:
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
