"""文档导出（提示词 05）—— schemas + repository + service + 5 exporters + api 单文件版

5 种格式：PDF（WeasyPrint）/ DOCX（python-docx）/ Markdown / CSV / TXT
多文档 ZIP 打包；下载 URL HMAC 签名；过期清理。
"""

from __future__ import annotations

import asyncio
import os
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal, Protocol
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func, select
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.auth.dependencies import get_current_user, require_permission
from app.common.config import settings
from app.common.database import Base, get_db
from app.common.exceptions import ForbiddenException, NotFoundException, ValidationException
from app.common.models import User
from app.common.schemas import APIResponse, PaginatedData
from app.exports._shared.signing import is_expired, sign_download_token, verify_download_token
from app.exports._shared.storage import root, task_file_path
from app.rag._shared.audit_helper import audit

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/exports", tags=["exports"])


# ============================================================
# ORM 模型
# ============================================================
ExportFormat = Literal["pdf", "docx", "markdown", "csv", "txt"]
ExportStatus = Literal["pending", "running", "done", "failed", "expired", "cancelled"]


class ExportTask(Base):
    __tablename__ = "export_tasks"
    __table_args__ = (
        Index("ix_export_user_status", "user_id", "status"),
        Index("ix_export_expires", "expires_at"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False).with_variant(String(36), "sqlite"),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    format: Mapped[str] = mapped_column(String(16), nullable=False)
    document_ids: Mapped[list[str]] = mapped_column(
        ARRAY(UUID(as_uuid=False).with_variant(String(36), "sqlite")), nullable=False
    )
    options: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ============================================================
# Schemas
# ============================================================
class ExportOptions(BaseModel):
    include_citations: bool = True
    include_assets: bool = True
    include_toc: bool = True
    template: Literal["default", "academic", "minimal"] = "default"
    page_size: Literal["A4", "Letter", "A3"] = "A4"
    font_size: int = 12
    language: str = "zh-CN"


class CreateExportRequest(BaseModel):
    format: ExportFormat
    document_ids: list[str] = Field(min_length=1, max_length=50)
    options: ExportOptions = Field(default_factory=ExportOptions)


class ExportTaskResponse(BaseModel):
    id: str
    user_id: str
    format: ExportFormat
    document_ids: list[str]
    options: ExportOptions
    status: ExportStatus
    progress: int
    file_path: str | None = None
    file_size: int | None = None
    download_url: str | None = None
    expires_at: datetime
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    finished_at: datetime | None = None
    model_config = {"from_attributes": True}


# ============================================================
# Exporter 抽象与实现（提示词 05 §4.2）
# ============================================================
class ExportContent:
    def __init__(
        self,
        document_id: str,
        title: str,
        markdown: str,
        assets: list[Path] | None = None,
        citations: list[dict] | None = None,
        metadata: dict | None = None,
    ):
        self.document_id = document_id
        self.title = title
        self.markdown = markdown
        self.assets = assets or []
        self.citations = citations or []
        self.metadata = metadata or {}


class Exporter(Protocol):
    format_name: str

    async def export(
        self, content: ExportContent, output_path: str, options: ExportOptions
    ) -> str: ...


class MarkdownExporter:
    format_name = "markdown"

    async def export(self, content: ExportContent, output_path: str, options: ExportOptions) -> str:
        body = f"# {content.title}\n\n{content.markdown}\n"
        if options.include_citations and content.citations:
            body += "\n## 引用\n\n" + "\n".join(
                f"- doc={c.get('doc_id')} chunk={c.get('chunk_id')} score={c.get('score')}"
                for c in content.citations
            )
        Path(output_path).write_text(body, encoding="utf-8")
        return output_path


class TxtExporter:
    format_name = "txt"

    async def export(self, content: ExportContent, output_path: str, options: ExportOptions) -> str:
        from markdown_it import MarkdownIt

        md = MarkdownIt().render(content.markdown)
        Path(output_path).write_text(f"{content.title}\n\n{md}", encoding="utf-8")
        return output_path


class CsvExporter:
    format_name = "csv"

    async def export(self, content: ExportContent, output_path: str, options: ExportOptions) -> str:
        import csv

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["section", "content"])
            writer.writerow(["title", content.title])
            for line in content.markdown.split("\n"):
                writer.writerow(["body", line])
        return output_path


class DocxExporter:
    format_name = "docx"

    async def export(self, content: ExportContent, output_path: str, options: ExportOptions) -> str:
        try:
            from docx import Document  # python-docx
        except ImportError as exc:
            raise RuntimeError("python-docx 未安装") from exc
        doc = Document()
        doc.add_heading(content.title, level=1)
        for line in content.markdown.split("\n"):
            if line.startswith("# "):
                doc.add_heading(line[2:], level=2)
            elif line.startswith("## "):
                doc.add_heading(line[3:], level=3)
            elif line.strip():
                doc.add_paragraph(line)
        if options.include_citations and content.citations:
            doc.add_heading("引用", level=2)
            for c in content.citations:
                doc.add_paragraph(
                    f"doc={c.get('doc_id')} chunk={c.get('chunk_id')} score={c.get('score')}",
                    style="List Bullet",
                )
        doc.save(output_path)
        return output_path


class PdfExporter:
    format_name = "pdf"

    async def export(self, content: ExportContent, output_path: str, options: ExportOptions) -> str:
        try:
            from weasyprint import HTML
        except ImportError as exc:
            raise RuntimeError("weasyprint 未安装") from exc
        body_html = _markdown_to_html(content.markdown)
        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
        @page {{ size: {options.page_size}; margin: 2cm; }}
        body {{
            font-family: 'Noto Sans CJK SC', sans-serif;
            font-size: {options.font_size}pt;
            line-height: 1.6;
        }}
        h1 {{ font-size: {options.font_size + 6}pt; }}
        h2 {{ font-size: {options.font_size + 4}pt; }}
        </style></head><body>
        <h1>{_escape(content.title)}</h1>
        {body_html}
        </body></html>"""
        HTML(string=html, base_url=str(root())).write_pdf(output_path)
        return output_path


def _markdown_to_html(md_text: str) -> str:
    try:
        from markdown_it import MarkdownIt
    except ImportError:
        return f"<pre>{_escape(md_text)}</pre>"
    return MarkdownIt().render(md_text)


def _escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


EXPORTERS: dict[str, Exporter] = {
    "markdown": MarkdownExporter(),
    "txt": TxtExporter(),
    "csv": CsvExporter(),
    "docx": DocxExporter(),
    "pdf": PdfExporter(),
}


# ============================================================
# ZIP 打包
# ============================================================
def zip_documents(*, task_id: str, files: list[str]) -> str:
    """打包多文档为单一 ZIP；返回 zip 路径。"""
    out_path = task_file_path(task_id, f"{task_id}.zip")
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for fp in files:
            arcname = os.path.basename(fp)
            zf.write(fp, arcname=arcname)
    return out_path


# ============================================================
# 文档内容获取（占位 - 员工4 文档服务就绪后接真实数据）
# ============================================================
async def _fetch_document_content(document_id: str) -> ExportContent:
    """从员工4 documents 模块获取内容。本期占位：返回 fixture Markdown。

    TODO 员工4 就绪后：调用 documents.service.get_markdown(document_id)
    """
    return ExportContent(
        document_id=document_id,
        title=f"文档 {document_id[:8]}",
        markdown=f"# {document_id[:8]}\n\n这是占位内容，员工4 文档服务就绪后会自动接入真实数据。",
    )


# ============================================================
# 任务执行
# ============================================================
async def _run_export(db: AsyncSession, task_id: str) -> None:
    """执行导出任务（arq 异步 / 测试同步调用都复用此函数）。"""
    task = await db.get(ExportTask, task_id)
    if task is None:
        return
    task.status = "running"
    task.progress = 0
    await db.commit()

    files: list[str] = []
    try:
        for i, doc_id in enumerate(task.document_ids):
            content = await _fetch_document_content(doc_id)
            exporter = EXPORTERS.get(task.format)
            if exporter is None:
                raise ValidationException(message=f"unsupported format: {task.format}")
            opts = ExportOptions.model_validate(task.options or {})
            ext = task.format if task.format != "markdown" else "md"
            filename = f"{i + 1:02d}_{doc_id[:8]}.{ext}"
            output_path = task_file_path(task_id, filename)
            await exporter.export(content, output_path, opts)
            files.append(output_path)
            task.progress = int((i + 1) / len(task.document_ids) * 100)
            await db.commit()

        # 单文档直接返回；多文档打 ZIP
        if len(files) == 1:
            final = files[0]
        else:
            final = zip_documents(task_id=task_id, files=files)

        task.file_path = final
        task.file_size = os.path.getsize(final)
        task.status = "done"
        task.finished_at = datetime.now(timezone.utc)
    except Exception as exc:
        logger.exception("export_failed", task_id=task_id)
        task.status = "failed"
        task.error_code = "export_failed"
        task.error_message = str(exc)[:512]
        task.finished_at = datetime.now(timezone.utc)
    await db.commit()


# ============================================================
# 过期清理（提示词 05 §4.7）
# ============================================================
async def cleanup_expired(db: AsyncSession) -> int:
    """把过期的 task 标记 expired 并删除文件。返回清理数。"""
    now = datetime.now(timezone.utc)
    res = await db.execute(
        select(ExportTask).where(ExportTask.expires_at < now, ExportTask.status != "expired")
    )
    tasks = res.scalars().all()
    count = 0
    for task in tasks:
        if task.file_path and os.path.exists(task.file_path):
            try:
                os.remove(task.file_path)
            except OSError:
                pass
        task.status = "expired"
        count += 1
    await db.commit()
    return count


# ============================================================
# 路由
# ============================================================
def _task_to_response(task: ExportTask) -> dict:
    download_url = None
    if task.status == "done" and task.file_path:
        expires = int(task.expires_at.timestamp())
        token = sign_download_token(
            export_id=task.id, user_id=task.user_id, expires_at_unix=expires
        )
        download_url = f"/api/v1/exports/{task.id}/download?token={token}&expires={expires}"
    return {
        "id": task.id,
        "user_id": task.user_id,
        "format": task.format,
        "document_ids": task.document_ids,
        "options": task.options or {},
        "status": task.status,
        "progress": task.progress,
        "file_path": task.file_path,
        "file_size": task.file_size,
        "download_url": download_url,
        "expires_at": task.expires_at,
        "error_code": task.error_code,
        "error_message": task.error_message,
        "created_at": task.created_at,
        "finished_at": task.finished_at,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_export_endpoint(
    request: Request,
    payload: CreateExportRequest,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("export:write")),
    db: AsyncSession = Depends(get_db),
):
    task = ExportTask(
        user_id=user.id,
        format=payload.format,
        document_ids=payload.document_ids,
        options=payload.options.model_dump(),
        status="pending",
        progress=0,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.export_default_ttl_hours),
    )
    db.add(task)
    await db.commit()
    await audit(
        db,
        action="export_create",
        user_id=user.id,
        resource_type="export_task",
        resource_id=task.id,
        request=request,
    )
    await db.commit()

    # 同步执行（生产用 arq 异步队列）
    try:
        await asyncio.wait_for(
            _run_export(db, task.id), timeout=settings.export_task_timeout_seconds
        )
    except asyncio.TimeoutError:
        logger.warning("export_timeout", task_id=task.id)
    return APIResponse(data=_task_to_response(task)).model_dump()


@router.get("")
async def list_exports_endpoint(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("export:read")),
    db: AsyncSession = Depends(get_db),
):
    q = select(ExportTask).where(ExportTask.user_id == user.id)
    if status_filter:
        q = q.where(ExportTask.status == status_filter)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
    offset = (page - 1) * page_size
    res = await db.execute(q.order_by(ExportTask.created_at.desc()).offset(offset).limit(page_size))
    items = [_task_to_response(t) for t in res.scalars().all()]
    return APIResponse(
        data=PaginatedData(items=items, page=page, page_size=page_size, total=total).model_dump()
    ).model_dump()


@router.get("/{export_id}")
async def get_export_endpoint(
    export_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("export:read")),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(ExportTask, export_id)
    if task is None:
        raise NotFoundException()
    if task.user_id != user.id:
        raise ForbiddenException()
    return APIResponse(data=_task_to_response(task)).model_dump()


@router.delete("/{export_id}")
async def delete_export_endpoint(
    export_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("export:delete")),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(ExportTask, export_id)
    if task is None:
        raise NotFoundException()
    if task.user_id != user.id:
        raise ForbiddenException()
    if task.file_path and os.path.exists(task.file_path):
        try:
            os.remove(task.file_path)
        except OSError:
            pass
    await db.delete(task)
    await db.commit()
    await audit(db, action="export_delete", user_id=user.id, resource_id=export_id, request=request)
    await db.commit()
    return APIResponse().model_dump()


@router.get("/{export_id}/download")
async def download_export_endpoint(
    export_id: str,
    request: Request,
    token: str = Query(...),
    expires: int = Query(...),
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("export:download")),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(ExportTask, export_id)
    if task is None:
        raise NotFoundException()
    if task.user_id != user.id:
        raise ForbiddenException(message="无权下载此文件")
    if is_expired(expires):
        raise NotFoundException(code=16001, message="下载链接已过期")
    if not verify_download_token(
        export_id=task.id, user_id=task.user_id, expires_at_unix=expires, token=token
    ):
        raise ForbiddenException(message="签名无效")
    if not task.file_path or not os.path.exists(task.file_path):
        raise NotFoundException()
    await audit(
        db, action="export_download", user_id=user.id, resource_id=export_id, request=request
    )
    await db.commit()
    return FileResponse(
        task.file_path,
        filename=os.path.basename(task.file_path),
        media_type="application/octet-stream",
    )


@router.post("/cleanup")
async def cleanup_endpoint(
    request: Request,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("export:delete")),
    db: AsyncSession = Depends(get_db),
):
    """管理员触发的过期清理；定时任务也会调用 _run_cleanup。"""
    count = await cleanup_expired(db)
    await audit(
        db, action="export_cleanup", user_id=user.id, detail=f"cleaned {count}", request=request
    )
    await db.commit()
    return APIResponse(data={"cleaned": count}).model_dump()
