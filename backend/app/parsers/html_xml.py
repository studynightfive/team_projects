"""HTML / XML / JSON parsers."""

from __future__ import annotations

import json
from pathlib import Path

from bs4 import BeautifulSoup
from pydantic import JsonValue, TypeAdapter

from app.parsers.base import DocumentParser, ParsedBlock, ParsedDocument
from app.parsers.text import decode_bytes

_JSON_ADAPTER: TypeAdapter[JsonValue] = TypeAdapter(JsonValue)


class HtmlParser(DocumentParser):
    name = "html"

    def supports(self, mime_type: str, extension: str) -> bool:
        return extension in {".html", ".htm"} or mime_type == "text/html"

    async def parse(self, source_path: str) -> ParsedDocument:
        path = Path(source_path)
        soup = BeautifulSoup(decode_bytes(path.read_bytes()), "lxml")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        title = (soup.title.string.strip() if soup.title and soup.title.string else path.stem)
        blocks: list[ParsedBlock] = []
        for el in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "pre", "table"]):
            text = el.get_text(" ", strip=True)
            if not text:
                continue
            if el.name.startswith("h"):
                blocks.append(
                    ParsedBlock(text=text, block_type="heading", level=int(el.name[1]), page_no=1)
                )
            elif el.name == "table":
                blocks.append(ParsedBlock(text=_table_to_md(el), block_type="table", page_no=1))
            elif el.name == "pre":
                blocks.append(ParsedBlock(text=text, block_type="code", page_no=1))
            else:
                blocks.append(ParsedBlock(text=text, block_type="paragraph", page_no=1))
        return ParsedDocument(
            title=title,
            blocks=blocks or [ParsedBlock(text="", block_type="paragraph", page_no=1)],
            page_count=1,
            parser_name=self.name,
        )


def _table_to_md(table) -> str:  # type: ignore[no-untyped-def]
    rows = []
    for tr in table.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
        if cells:
            rows.append(cells)
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    normalized = [r + [""] * (width - len(r)) for r in rows]
    lines = [
        "| " + " | ".join(normalized[0]) + " |",
        "| " + " | ".join("---" for _ in range(width)) + " |",
    ]
    for row in normalized[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


class XmlParser(DocumentParser):
    name = "xml"

    def supports(self, mime_type: str, extension: str) -> bool:
        return extension == ".xml" or mime_type in {"application/xml", "text/xml"}

    async def parse(self, source_path: str) -> ParsedDocument:
        path = Path(source_path)
        soup = BeautifulSoup(decode_bytes(path.read_bytes()), "lxml-xml")
        blocks: list[ParsedBlock] = []

        def walk(node, depth: int = 0) -> None:  # type: ignore[no-untyped-def]
            if getattr(node, "name", None) is None:
                return
            text = node.get_text(" ", strip=True)
            if text and len(list(node.children)) <= 1:
                blocks.append(
                    ParsedBlock(
                        text=f"{node.name}: {text}",
                        block_type="paragraph",
                        page_no=1,
                        metadata={"depth": depth},
                    )
                )
                return
            for child in node.children:
                if getattr(child, "name", None):
                    walk(child, depth + 1)

        root = soup.find()
        if root:
            walk(root)
        return ParsedDocument(
            title=path.stem,
            blocks=blocks or [ParsedBlock(text="(空 XML)", block_type="paragraph", page_no=1)],
            page_count=1,
            parser_name=self.name,
        )


class JsonParser(DocumentParser):
    name = "json"

    def supports(self, mime_type: str, extension: str) -> bool:
        return extension == ".json" or mime_type in {"application/json", "text/json"}

    async def parse(self, source_path: str) -> ParsedDocument:
        path = Path(source_path)
        data = _JSON_ADAPTER.validate_json(path.read_bytes())
        pretty = json.dumps(data, ensure_ascii=False, indent=2)
        title = path.stem
        if isinstance(data, dict):
            parsed_title = data.get("title")
            if isinstance(parsed_title, str):
                title = parsed_title
        return ParsedDocument(
            title=title,
            blocks=[ParsedBlock(text=pretty, block_type="code", page_no=1)],
            page_count=1,
            parser_name=self.name,
        )
