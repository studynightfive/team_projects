"""Unit tests for chunking / markdown / indexing (employee 4)."""

import pytest

from app.documents.chunking import Chunker
from app.documents.indexing import deterministic_embedding
from app.documents.markdown import MarkdownConverter, sanitize_markdown_html
from app.documents.storage import sanitize_filename
from app.parsers.base import ParsedBlock, ParsedDocument


def test_sanitize_filename_blocks_traversal() -> None:
    assert sanitize_filename("../../etc/passwd") == "passwd"


def test_sanitize_markdown_strips_script() -> None:
    dirty = '<a href="javascript:alert(1)">x</a><img src=x onerror=alert(1)>'
    clean = sanitize_markdown_html(dirty)
    assert "javascript" not in clean.lower()
    assert "onerror" not in clean.lower()


@pytest.mark.asyncio
async def test_chunker_and_embedding() -> None:
    md = "# 文档\n\n## 第一节\n\n段落一。\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n\n" + (
        "长文本。" * 40
    )
    chunks = await Chunker().split(md, {"chunk_size": 200, "chunk_overlap": 20})
    assert chunks
    vec = deterministic_embedding("知识库", 8)
    assert abs(sum(x * x for x in vec) - 1.0) < 1e-6


@pytest.mark.asyncio
async def test_chunker_prefers_markdown_headings_and_paragraphs() -> None:
    md = "# 文档\n\n## 第一节\n\n段落一。\n\n段落二。\n\n## 第二节\n\n段落三。"
    chunks = await Chunker().split(md, {"chunk_size": 800, "chunk_overlap": 120})
    contents = [chunk.content for chunk in chunks]

    assert "# 文档" in contents
    assert "## 第一节" in contents
    assert any(content == "## 第一节\n\n段落一。" for content in contents)
    assert any(content == "## 第一节\n\n段落二。" for content in contents)
    assert any(content == "## 第二节\n\n段落三。" for content in contents)
    assert not any("段落一。\n\n段落二。" in content for content in contents)


@pytest.mark.asyncio
@pytest.mark.parametrize("strategy", ["fixed", "semantic", "recursive", "format"])
async def test_chunker_supports_upload_strategies(strategy: str) -> None:
    md = "# 医疗信息化\n\n电子病历用于记录诊疗过程。\n\n" + "数据安全。" * 80
    chunks = await Chunker().split(
        md,
        {"chunk_size": 200, "chunk_overlap": 20},
        strategy=strategy,
    )

    assert chunks
    assert all(chunk.content for chunk in chunks)
    assert all(len(chunk.content) <= 220 for chunk in chunks)


@pytest.mark.asyncio
async def test_markdown_package() -> None:
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
    assert package.manifest["content_hash"] == "abc"
