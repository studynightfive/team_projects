"""Parser registry and routing."""

from __future__ import annotations

from pathlib import Path

from app.common.exceptions import AppException
from app.common.schemas import ErrorCode
from app.parsers.archive import ZIP_DOCUMENT_EXTENSIONS, validate_zip_container
from app.parsers.base import DocumentParser, ParsedDocument
from app.parsers.email_ebook import EmlParser, EpubParser
from app.parsers.html_xml import HtmlParser, JsonParser, XmlParser
from app.parsers.image_ocr import ImageParser
from app.parsers.office import (
    DocParser,
    DocxParser,
    OpenDocumentParser,
    PptParser,
    PptxParser,
    XlsParser,
    XlsxParser,
)
from app.parsers.pdf import PdfParser
from app.parsers.text import CsvParser, MarkdownParser, TextParser


class ParserRegistry:
    def __init__(self, parsers: list[DocumentParser] | None = None) -> None:
        self._parsers = parsers or default_parsers()

    def register(self, parser: DocumentParser) -> None:
        self._parsers.append(parser)

    def resolve(self, mime_type: str, extension: str) -> DocumentParser | None:
        extension = extension.lower() if extension.startswith(".") else f".{extension.lower()}"
        for parser in self._parsers:
            if parser.supports(mime_type, extension):
                return parser
        return None

    async def parse(self, source_path: str, mime_type: str, extension: str) -> ParsedDocument:
        normalized_extension = (
            extension.lower() if extension.startswith(".") else f".{extension.lower()}"
        )
        if normalized_extension in ZIP_DOCUMENT_EXTENSIONS:
            validate_zip_container(source_path)
        parser = self.resolve(mime_type, extension)
        if parser is None:
            raise AppException(code=ErrorCode.PARSER_NOT_FOUND, message=f"未找到解析器: ext={extension}, mime={mime_type}", status_code=422)
        parsed = await parser.parse(source_path)
        parsed.parser_name = parsed.parser_name or parser.name
        parsed.parser_version = parsed.parser_version or parser.version
        if not parsed.title:
            parsed.title = Path(source_path).stem
        return parsed


def default_parsers() -> list[DocumentParser]:
    return [
        PdfParser(),
        DocxParser(),
        DocParser(),
        XlsxParser(),
        XlsParser(),
        PptxParser(),
        PptParser(),
        MarkdownParser(),
        TextParser(),
        CsvParser(),
        HtmlParser(),
        XmlParser(),
        JsonParser(),
        EpubParser(),
        OpenDocumentParser(),
        ImageParser(),
        EmlParser(),
    ]


_REGISTRY: ParserRegistry | None = None


def get_parser_registry() -> ParserRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = ParserRegistry()
    return _REGISTRY
