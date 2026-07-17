"""Unit tests for MIME detection, parsers, markdown, chunking and indexing."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.common.exceptions import AppException
from app.documents.chunking import Chunker
from app.documents.indexing import DocumentIndexingService, deterministic_embedding
from app.documents.markdown import MarkdownConverter, sanitize_markdown_html
from app.documents.storage import compute_sha256, sanitize_filename
from app.parsers.mime import detect_file
from app.parsers.registry import get_parser_registry
from app.parsers.text import MarkdownParser, TextParser


def test_sanitize_filename_blocks_traversal() -> None:
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("正常 文件.pdf") == "正常_文件.pdf"


def test_detect_markdown_and_mismatch(samples_dir: Path) -> None:
    data = (samples_dir / "md" / "normal_zh.md").read_bytes()
    detected = detect_file("normal_zh.md", data)
    assert detected.extension == ".md"
    assert "text" in detected.detected_mime or detected.detected_mime in {
        "text/plain",
        "text/markdown",
        "text/x-markdown",
    }

    with pytest.raises(AppException):
        detect_file("fake.pdf", b"plain text pretending to be pdf")



@pytest.mark.asyncio
async def test_text_and_markdown_parsers(samples_dir: Path) -> None:
    text = await TextParser().parse(str(samples_dir / "txt" / "normal_en.txt"))
    assert text.blocks
    assert text.parser_name == "text"

    md = await MarkdownParser().parse(str(samples_dir / "md" / "normal_zh.md"))
    assert any(b.block_type == "heading" for b in md.blocks)


@pytest.mark.asyncio
async def test_html_strips_script(samples_dir: Path) -> None:
    parsed = await get_parser_registry().parse(
        str(samples_dir / "html" / "normal.html"),
        "text/html",
        ".html",
    )
    joined = "\n".join(b.text for b in parsed.blocks)
    assert "alert" not in joined
    assert "标题" in joined


@pytest.mark.asyncio
async def test_csv_json_eml(samples_dir: Path) -> None:
    registry = get_parser_registry()
    csv_doc = await registry.parse(str(samples_dir / "csv" / "normal.csv"), "text/csv", ".csv")
    assert csv_doc.blocks[0].block_type == "table"

    json_doc = await registry.parse(
        str(samples_dir / "json" / "normal.json"), "application/json", ".json"
    )
    assert "示例" in json_doc.title or "示例" in json_doc.blocks[0].text

    eml = await registry.parse(str(samples_dir / "eml" / "normal.eml"), "message/rfc822", ".eml")
    assert eml.blocks


@pytest.mark.asyncio
async def test_corrupt_pdf_manual_review(samples_dir: Path) -> None:
    parsed = await get_parser_registry().parse(
        str(samples_dir / "pdf" / "corrupt.pdf"),
        "application/pdf",
        ".pdf",
    )
    assert parsed.manual_review or parsed.warnings


@pytest.mark.asyncio
async def test_markdown_sanitize_and_package() -> None:
    dirty = '<a href="javascript:alert(1)">x</a><img src=x onerror=alert(1)>'
    clean = sanitize_markdown_html(dirty)
    assert "javascript" not in clean.lower()
    assert "onerror" not in clean.lower()

    from app.parsers.base import ParsedBlock, ParsedDocument

    parsed = ParsedDocument(
        title="标题",
        blocks=[
            ParsedBlock(text="<!-- page:1 -->", block_type="meta", page_no=1),
            ParsedBlock(text="正文", block_type="paragraph", page_no=1, confidence=0.9),
        ],
        parser_name="test",
        page_count=1,
    )
    package = await MarkdownConverter().convert(
        parsed, content_hash="abc", original_filename="a.md"
    )
    assert package.content_md.startswith("# 标题")
    assert "page-1" in package.content_md
    assert package.manifest["content_hash"] == "abc"


@pytest.mark.asyncio
async def test_chunker_keeps_table_and_overlap() -> None:
    md = """# 文档

## 第一节

段落一。

| A | B |
| --- | --- |
| 1 | 2 |

## 第二节

""" + ("长文本。" * 80)
    chunks = await Chunker().split(md, {"chunk_size": 200, "chunk_overlap": 20})
    assert chunks
    assert any("|" in c.content for c in chunks)


def test_deterministic_embedding_stable() -> None:
    a = deterministic_embedding("知识库检索", 8)
    b = deterministic_embedding("知识库检索", 8)
    assert a == b
    assert abs(sum(x * x for x in a) - 1.0) < 1e-6


def test_compute_hash() -> None:
    assert compute_sha256(b"abc") == compute_sha256(b"abc")
    assert compute_sha256(b"abc") != compute_sha256(b"abcd")


def test_search_document_builder() -> None:
    from app.documents.chunking import Chunk

    svc = DocumentIndexingService()
    chunk = Chunk(1, "关键词 测试", None, None, 1, 0, 10, 2)
    doc = svc.build_search_document(chunk, document_id="d1", title="t")
    assert "关键词" in doc["lexeme"]
