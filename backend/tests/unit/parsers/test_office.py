"""Office parser smoke tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.parsers.registry import get_parser_registry


@pytest.mark.asyncio
async def test_docx_xlsx_pptx(samples_dir: Path) -> None:
    registry = get_parser_registry()
    docx = await registry.parse(
        str(samples_dir / "docx" / "normal_zh.docx"),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".docx",
    )
    assert any("检索" in b.text or "正文" in b.text for b in docx.blocks)

    xlsx = await registry.parse(
        str(samples_dir / "xlsx" / "normal_zh.xlsx"),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xlsx",
    )
    assert any(b.block_type == "table" for b in xlsx.blocks)

    pptx = await registry.parse(
        str(samples_dir / "pptx" / "normal_zh.pptx"),
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".pptx",
    )
    assert pptx.page_count >= 1
