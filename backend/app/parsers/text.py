"""Text, Markdown, CSV/TSV parsers."""

from __future__ import annotations

from pathlib import Path

import chardet

from app.parsers.base import DocumentParser, ParsedBlock, ParsedDocument


def decode_bytes(data: bytes) -> str:
    detected = chardet.detect(data) or {}
    encoding = detected.get("encoding") or "utf-8"
    try:
        return data.decode(encoding)
    except Exception:
        return data.decode("utf-8", errors="replace")


class TextParser(DocumentParser):
    name = "text"

    def supports(self, mime_type: str, extension: str) -> bool:
        return extension in {".txt", ".log", ".rst", ".org"} or mime_type.startswith("text/plain")

    async def parse(self, source_path: str) -> ParsedDocument:
        path = Path(source_path)
        text = decode_bytes(path.read_bytes())
        blocks = [
            ParsedBlock(text=line, block_type="paragraph", page_no=1)
            for line in text.splitlines()
            if line.strip()
        ]
        if not blocks:
            blocks = [ParsedBlock(text="", block_type="paragraph", page_no=1)]
        return ParsedDocument(
            title=path.stem,
            blocks=blocks,
            page_count=1,
            parser_name=self.name,
            parser_version=self.version,
        )


class MarkdownParser(DocumentParser):
    name = "markdown"

    def supports(self, mime_type: str, extension: str) -> bool:
        return extension in {".md", ".markdown"} or "markdown" in mime_type

    async def parse(self, source_path: str) -> ParsedDocument:
        path = Path(source_path)
        text = decode_bytes(path.read_bytes())
        blocks: list[ParsedBlock] = []
        title = path.stem
        table_buf: list[str] = []

        def flush_table() -> None:
            nonlocal table_buf
            if table_buf:
                blocks.append(ParsedBlock(text="\n".join(table_buf), block_type="table", page_no=1))
                table_buf = []

        for line in text.splitlines():
            if line.strip().startswith("|"):
                table_buf.append(line)
                continue
            flush_table()
            if line.startswith("#"):
                level = len(line) - len(line.lstrip("#"))
                heading = line.lstrip("# ").strip()
                if level == 1 and title == path.stem:
                    title = heading
                blocks.append(
                    ParsedBlock(
                        text=heading,
                        block_type="heading",
                        level=min(level, 6),
                        page_no=1,
                    )
                )
            elif line.strip():
                blocks.append(ParsedBlock(text=line, block_type="paragraph", page_no=1))
        flush_table()
        return ParsedDocument(
            title=title,
            blocks=blocks or [ParsedBlock(text="", block_type="paragraph", page_no=1)],
            page_count=1,
            parser_name=self.name,
            parser_version=self.version,
        )


class CsvParser(DocumentParser):
    name = "csv"

    def supports(self, mime_type: str, extension: str) -> bool:
        return extension in {".csv", ".tsv"} or mime_type in {
            "text/csv",
            "text/tab-separated-values",
            "application/csv",
        }

    async def parse(self, source_path: str) -> ParsedDocument:
        import csv
        from io import StringIO

        path = Path(source_path)
        text = decode_bytes(path.read_bytes())
        delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
        reader = csv.reader(StringIO(text), delimiter=delimiter)
        rows = list(reader)
        if not rows:
            return ParsedDocument(
                title=path.stem,
                blocks=[ParsedBlock(text="(空表格)", block_type="paragraph", page_no=1)],
                page_count=1,
                parser_name=self.name,
                warnings=["empty csv"],
            )
        header = rows[0]
        md_lines = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join("---" for _ in header) + " |",
        ]
        for row in rows[1:]:
            padded = row + [""] * (len(header) - len(row))
            md_lines.append("| " + " | ".join(padded[: len(header)]) + " |")
        return ParsedDocument(
            title=path.stem,
            blocks=[
                ParsedBlock(text="\n".join(md_lines), block_type="table", page_no=1, sheet_name="sheet1")
            ],
            page_count=1,
            parser_name=self.name,
            parser_version=self.version,
        )
