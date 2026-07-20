"""Email (.eml) and EPUB parsers."""

from __future__ import annotations

import email
from email import policy
from pathlib import Path

from pydantic import JsonValue

from app.parsers.base import DocumentParser, ParsedBlock, ParsedDocument
from app.parsers.text import decode_bytes


class EmlParser(DocumentParser):
    name = "eml"

    def supports(self, mime_type: str, extension: str) -> bool:
        return extension == ".eml" or mime_type == "message/rfc822"

    async def parse(self, source_path: str) -> ParsedDocument:
        path = Path(source_path)
        msg = email.message_from_bytes(path.read_bytes(), policy=policy.default)
        subject = str(msg.get("subject") or path.stem)
        sender = str(msg.get("from") or "")
        to = str(msg.get("to") or "")
        blocks: list[ParsedBlock] = [
            ParsedBlock(text=subject, block_type="heading", level=1, page_no=1),
            ParsedBlock(text=f"发件人: {sender}", block_type="paragraph", page_no=1),
            ParsedBlock(text=f"收件人: {to}", block_type="paragraph", page_no=1),
        ]
        body = ""
        attachments: list[str] = []
        if msg.is_multipart():
            for part in msg.walk():
                filename = part.get_filename()
                if filename:
                    attachments.append(filename)
                    continue
                ctype = part.get_content_type()
                if ctype == "text/plain" and not body:
                    body = part.get_content()
                elif ctype == "text/html" and not body:
                    from bs4 import BeautifulSoup

                    body = BeautifulSoup(part.get_content(), "lxml").get_text("\n", strip=True)
        else:
            body = msg.get_content() if msg.get_content_type().startswith("text/") else ""

        if isinstance(body, bytes):
            body = decode_bytes(body)
        if body:
            for para in str(body).split("\n\n"):
                para = para.strip()
                if para:
                    blocks.append(ParsedBlock(text=para, block_type="paragraph", page_no=1))
        if attachments:
            attachment_metadata: list[JsonValue] = list(attachments)
            blocks.append(
                ParsedBlock(
                    text="附件: " + ", ".join(attachments),
                    block_type="paragraph",
                    page_no=1,
                    metadata={"attachments": attachment_metadata},
                )
            )
        return ParsedDocument(
            title=subject,
            blocks=blocks,
            page_count=1,
            parser_name=self.name,
            source_metadata={"from": sender, "to": to},
        )


class EpubParser(DocumentParser):
    name = "epub"

    def supports(self, mime_type: str, extension: str) -> bool:
        return extension == ".epub" or mime_type == "application/epub+zip"

    async def parse(self, source_path: str) -> ParsedDocument:
        from bs4 import BeautifulSoup
        from ebooklib import epub

        path = Path(source_path)
        book = epub.read_epub(str(path))
        title = path.stem
        try:
            title_meta = book.get_metadata("DC", "title")
            if title_meta:
                title = str(title_meta[0][0])
        except Exception:
            pass
        blocks: list[ParsedBlock] = [
            ParsedBlock(text=title, block_type="heading", level=1, page_no=1)
        ]
        page = 0
        for item in book.get_items():
            if item.get_type() != 9:  # ITEM_DOCUMENT
                continue
            page += 1
            soup = BeautifulSoup(item.get_content(), "lxml")
            for tag in soup(["script", "style"]):
                tag.decompose()
            for el in soup.find_all(["h1", "h2", "h3", "p", "li"]):
                text = el.get_text(" ", strip=True)
                if not text:
                    continue
                if el.name.startswith("h"):
                    blocks.append(
                        ParsedBlock(
                            text=text,
                            block_type="heading",
                            level=int(el.name[1]),
                            page_no=page,
                        )
                    )
                else:
                    blocks.append(ParsedBlock(text=text, block_type="paragraph", page_no=page))
        return ParsedDocument(
            title=title,
            blocks=blocks or [ParsedBlock(text="", block_type="paragraph", page_no=1)],
            page_count=page or 1,
            parser_name=self.name,
        )
