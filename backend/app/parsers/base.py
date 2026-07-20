"""Parser domain objects and abstract interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from pydantic import JsonValue

PARSER_VERSION = "1.0.0"


@dataclass
class ParsedBlock:
    text: str
    block_type: str = "paragraph"  # paragraph|heading|table|code|list|image|meta
    level: int | None = None
    page_no: int | None = None
    sheet_name: str | None = None
    slide_no: int | None = None
    confidence: float | None = None
    metadata: dict[str, JsonValue] = field(default_factory=dict)


@dataclass
class ParsedAsset:
    filename: str
    data: bytes
    mime_type: str
    page_no: int | None = None
    description: str = ""


@dataclass
class ParsedDocument:
    title: str
    blocks: list[ParsedBlock]
    assets: list[ParsedAsset] = field(default_factory=list)
    page_count: int | None = None
    parser_name: str = ""
    parser_version: str = PARSER_VERSION
    warnings: list[str] = field(default_factory=list)
    source_metadata: dict[str, JsonValue] = field(default_factory=dict)
    needs_ocr: bool = False
    manual_review: bool = False


class DocumentParser(ABC):
    name: str = "base"
    version: str = PARSER_VERSION

    @abstractmethod
    def supports(self, mime_type: str, extension: str) -> bool:
        ...

    @abstractmethod
    async def parse(self, source_path: str) -> ParsedDocument:
        ...
