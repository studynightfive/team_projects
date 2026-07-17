"""Document upload, processing pipeline, retry and query services."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import Settings, settings as app_settings
from app.common.exceptions import AppException, ForbiddenException, NotFoundException
from app.common.models import User
from app.common.schemas import ErrorCode
from app.documents.chunking import Chunker
from app.documents.indexing import DocumentIndexingService
from app.documents.markdown import MarkdownConverter
from app.documents.models import (
    Document,
    DocumentAsset,
    DocumentChunk,
    DocumentStatus,
    DocumentTask,
    DuplicatePolicy,
    TaskStatus,
)
from app.documents.permissions import require_any_permission, user_can_access_kb
from app.documents.schemas import (
    ChunkItem,
    DocumentDetail,
    DocumentSummary,
    MarkdownContent,
    ReprocessRequest,
    TaskResponse,
    UploadOptions,
    UploadResponse,
    UploadResultItem,
)
from app.documents.storage import DocumentStorage, compute_sha256
from app.knowledge.models import KnowledgeBase
from app.parsers.mime import detect_file
from app.parsers.pdf import enrich_pdf_with_ocr
from app.parsers.registry import get_parser_registry


def get_settings() -> Settings:
    return app_settings


def new_request_id() -> str:
    return str(uuid.uuid4())

STAGE_PROGRESS = {
    DocumentStatus.UPLOADED.value: 5,
    DocumentStatus.DETECTING.value: 15,
    DocumentStatus.CONVERTING.value: 35,
    DocumentStatus.OCR.value: 50,
    DocumentStatus.NORMALIZING.value: 65,
    DocumentStatus.CHUNKING.value: 80,
    DocumentStatus.INDEXING.value: 90,
    DocumentStatus.READY.value: 100,
    DocumentStatus.FAILED.value: 100,
    DocumentStatus.MANUAL_REVIEW.value: 100,
}


class DocumentService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
        storage: DocumentStorage | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.storage = storage or DocumentStorage(self.settings)
        self.registry = get_parser_registry()
        self.markdown = MarkdownConverter()
        self.chunker = Chunker(self.settings)
        self.indexer = DocumentIndexingService(self.settings)

    async def _get_kb(self, kb_id: str) -> KnowledgeBase:
        kb = await self.session.get(KnowledgeBase, kb_id)
        if kb is None:
            raise NotFoundException(code=ErrorCode.KB_NOT_FOUND, message="知识库不存在")
        return kb

    async def list_documents(
        self,
        user: User,
        kb_id: str,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DocumentSummary], int]:
        if not await user_can_access_kb(self.session, user, str(kb_id)):
            raise ForbiddenException(message="无权访问该知识库")
        await self._get_kb(kb_id)
        total_stmt = select(Document).where(Document.knowledge_base_id == kb_id)
        result = await self.session.execute(total_stmt)
        all_docs = list(result.scalars())
        total = len(all_docs)
        start = (page - 1) * page_size
        items = all_docs[start : start + page_size]
        return [DocumentSummary.model_validate(d) for d in items], total

    async def get_document(self, user: User, document_id: str) -> DocumentDetail:
        doc = await self.session.get(Document, document_id)
        if doc is None:
            raise NotFoundException(code=ErrorCode.DOCUMENT_NOT_FOUND, message="文档不存在")
        if not await user_can_access_kb(self.session, user, str(doc.knowledge_base_id)):
            raise ForbiddenException(message="无权访问该知识库")
        return DocumentDetail.model_validate(doc)

    async def get_markdown(self, user: User, document_id: str) -> MarkdownContent:
        doc = await self.get_document(user, document_id)
        if doc.status != DocumentStatus.READY.value:
            raise AppException(code=ErrorCode.DOCUMENT_NOT_FOUND, message="文档尚未就绪", status_code=409)
        content = self.storage.read_markdown(document_id)
        manifest = self.storage.read_manifest(document_id)
        return MarkdownContent(document_id=document_id, content=content, manifest=manifest)

    async def get_chunks(
        self,
        user: User,
        document_id: str,
        *,
        active_only: bool = True,
    ) -> list[ChunkItem]:
        await self.get_document(user, document_id)
        stmt = select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        if active_only:
            stmt = stmt.where(DocumentChunk.is_active.is_(True))
        stmt = stmt.order_by(DocumentChunk.chunk_no)
        result = await self.session.execute(stmt)
        return [ChunkItem.model_validate(c) for c in result.scalars()]

    async def get_asset_path(
        self, user: User, document_id: str, asset_id: str
    ) -> Path:
        await self.get_document(user, document_id)
        asset = await self.session.get(DocumentAsset, asset_id)
        if asset is None or asset.document_id != document_id:
            raise NotFoundException(code=ErrorCode.ASSET_NOT_FOUND, message="资源不存在")
        path = self.storage.resolve_asset(document_id, asset.relative_path)
        if not path.exists():
            raise NotFoundException(code=ErrorCode.ASSET_NOT_FOUND, message="资源文件缺失")
        return path

    async def get_task(self, user: User, task_id: str) -> TaskResponse:
        task = await self.session.get(DocumentTask, task_id)
        if task is None:
            raise NotFoundException(code=ErrorCode.TASK_NOT_FOUND, message="任务不存在")
        doc = await self.session.get(Document, task.document_id)
        if doc is None:
            raise NotFoundException(code=ErrorCode.DOCUMENT_NOT_FOUND, message="文档不存在")
        if not await user_can_access_kb(self.session, user, str(doc.knowledge_base_id)):
            raise ForbiddenException(message="无权访问该知识库")
        require_any_permission(user, "admin.task.view", "admin.document.view", "document.view")
        return TaskResponse.from_orm_task(task)

    async def upload(
        self,
        user: User,
        kb_id: str,
        files: list[tuple[str, bytes]],
        options: UploadOptions,
    ) -> UploadResponse:
        require_any_permission(user, "admin.document.upload", "admin.document.view")
        if not await user_can_access_kb(self.session, user, str(kb_id)):
            raise ForbiddenException(message="无权访问该知识库")
        await self._get_kb(kb_id)

        if not files:
            raise AppException(code=ErrorCode.UPLOAD_INVALID, message="未上传文件", status_code=400)
        if len(files) > self.settings.max_upload_files:
            raise AppException(code=ErrorCode.UPLOAD_INVALID, message=f"单次最多上传 {self.settings.max_upload_files} 个文件", status_code=400)

        items: list[UploadResultItem] = []
        for filename, data in files:
            items.append(await self._upload_one(user, kb_id, filename, data, options))
        await self.session.commit()
        return UploadResponse(items=items)

    async def _upload_one(
        self,
        user: User,
        kb_id: str,
        filename: str,
        data: bytes,
        options: UploadOptions,
    ) -> UploadResultItem:
        if len(data) > self.settings.max_upload_bytes:
            raise AppException(code=ErrorCode.UPLOAD_TOO_LARGE, message="文件超过大小限制", status_code=413)

        detected = detect_file(filename, data)
        if detected.extension and detected.extension not in self.settings.allowed_extensions:
            # Keep original, mark for manual review via processing pipeline
            pass

        content_hash = compute_sha256(data)
        existing = await self._find_by_hash(kb_id, content_hash)

        if existing and options.duplicate_policy == DuplicatePolicy.SKIP:
            latest_task = await self._latest_task(existing.id)
            return UploadResultItem(
                document=DocumentSummary.model_validate(existing),
                task_id=latest_task.id if latest_task else existing.id,
                skipped=True,
                message="duplicate skipped",
            )

        version = 1
        if existing and options.duplicate_policy == DuplicatePolicy.NEW_VERSION:
            version = existing.version + 1
        elif existing and options.duplicate_policy == DuplicatePolicy.REPLACE:
            await self._deactivate_index(existing.id)
            version = existing.version
            # Soft-replace: create new document row sharing version bump avoidance
            version = existing.version
        elif existing and options.duplicate_policy not in DuplicatePolicy:
            raise AppException(code=ErrorCode.DUPLICATE_POLICY, message="不支持的 duplicate_policy", status_code=400)

        if existing and options.duplicate_policy == DuplicatePolicy.REPLACE:
            document = existing
            document.original_filename = detected.filename
            document.stored_filename = detected.filename
            document.extension = detected.extension
            document.mime_type = detected.detected_mime
            document.size_bytes = len(data)
            document.content_hash = content_hash
            document.status = DocumentStatus.UPLOADED.value
            document.ocr_enabled = options.ocr_enabled
            document.language = options.language
            document.folder_path = options.folder_path
            document.error_code = None
            document.error_message = None
            document.is_active_index = False
            self.storage.clear_derived(document.id)
            self.storage.save_original(document.id, detected.filename, data)
        else:
            document = Document(
                id=str(uuid.uuid4()),
                knowledge_base_id=kb_id,
                title=Path(detected.filename).stem,
                original_filename=detected.filename,
                stored_filename=detected.filename,
                folder_path=options.folder_path,
                extension=detected.extension or ".bin",
                mime_type=detected.detected_mime,
                size_bytes=len(data),
                content_hash=content_hash,
                version=version,
                status=DocumentStatus.UPLOADED.value,
                ocr_enabled=options.ocr_enabled,
                language=options.language,
                created_by=str(user.id),
            )
            self.session.add(document)
            await self.session.flush()
            self.storage.save_original(document.id, detected.filename, data)

        request_id = new_request_id()
        task = DocumentTask(
            id=str(uuid.uuid4()),
            document_id=document.id,
            task_type="document_convert",
            status=TaskStatus.QUEUED.value,
            stage=DocumentStatus.UPLOADED.value,
            progress=STAGE_PROGRESS[DocumentStatus.UPLOADED.value],
            retry_count=0,
            idempotency_key=f"{document.id}:{content_hash}:v{document.version}",
            request_id=request_id,
        )
        self.session.add(task)
        await self.session.flush()

        if self.settings.worker_inline:
            await self.process_document(document.id, task.id)

        await self.session.refresh(document)
        await self.session.refresh(task)
        return UploadResultItem(
            document=DocumentSummary.model_validate(document),
            task_id=task.id,
        )

    async def reprocess(
        self,
        user: User,
        document_id: str,
        body: ReprocessRequest | None = None,
    ) -> TaskResponse:
        require_any_permission(user, "admin.document.upload")
        doc = await self.session.get(Document, document_id)
        if doc is None:
            raise NotFoundException(code=ErrorCode.DOCUMENT_NOT_FOUND, message="文档不存在")
        if not await user_can_access_kb(self.session, user, str(doc.knowledge_base_id)):
            raise ForbiddenException(message="无权访问该知识库")

        if doc.status not in {
            DocumentStatus.FAILED.value,
            DocumentStatus.MANUAL_REVIEW.value,
            DocumentStatus.READY.value,
        }:
            raise AppException(code=ErrorCode.TASK_NOT_RETRYABLE, message="当前状态不可重试", status_code=409)

        if body:
            if body.ocr_enabled is not None:
                doc.ocr_enabled = body.ocr_enabled
            if body.language:
                doc.language = body.language

        latest = await self._latest_task(doc.id)
        retry_count = (latest.retry_count + 1) if latest else 1
        request_id = new_request_id()
        task = DocumentTask(
            id=str(uuid.uuid4()),
            document_id=doc.id,
            task_type="document_convert",
            status=TaskStatus.QUEUED.value,
            stage=DocumentStatus.UPLOADED.value,
            progress=0,
            retry_count=retry_count,
            idempotency_key=f"{doc.id}:{doc.content_hash}:retry:{retry_count}",
            request_id=request_id,
        )
        self.session.add(task)
        doc.status = DocumentStatus.UPLOADED.value
        doc.error_code = None
        doc.error_message = None
        await self.session.flush()

        if self.settings.worker_inline:
            await self.process_document(doc.id, task.id)
        await self.session.commit()
        await self.session.refresh(task)
        return TaskResponse.from_orm_task(task)

    async def delete_document(self, user: User, document_id: str) -> None:
        require_any_permission(user, "admin.document.delete")
        doc = await self.session.get(Document, document_id)
        if doc is None:
            raise NotFoundException(code=ErrorCode.DOCUMENT_NOT_FOUND, message="文档不存在")
        if not await user_can_access_kb(self.session, user, str(doc.knowledge_base_id)):
            raise ForbiddenException(message="无权访问该知识库")
        await self._deactivate_index(doc.id)
        await self.session.delete(doc)
        await self.session.commit()

    async def process_document(self, document_id: str, task_id: str) -> None:
        doc = await self.session.get(Document, document_id)
        task = await self.session.get(DocumentTask, task_id)
        if doc is None or task is None:
            return

        task.status = TaskStatus.RUNNING.value
        task.started_at = datetime.now(timezone.utc)
        await self.session.flush()

        try:
            await self._run_pipeline(doc, task)
        except AppException as exc:
            await self._fail(doc, task, exc.code, exc.message, manual=exc.code == ErrorCode.MANUAL_REVIEW)
        except Exception as exc:  # noqa: BLE001
            await self._fail(doc, task, ErrorCode.PARSE_FAILED, f"处理失败: {exc}")

    async def _run_pipeline(self, doc: Document, task: DocumentTask) -> None:
        original = self.storage.original_dir(doc.id) / doc.stored_filename
        if not original.exists():
            # fallback: any file in original
            files = list(self.storage.original_dir(doc.id).glob("*"))
            if not files:
                raise NotFoundException(code=ErrorCode.DOCUMENT_NOT_FOUND, message="原始文件不存在")
            original = files[0]

        await self._set_stage(doc, task, DocumentStatus.DETECTING)
        if doc.extension not in self.settings.allowed_extensions:
            raise AppException(code=ErrorCode.MANUAL_REVIEW, message="未知或不受支持的格式，已保留原件", status_code=422)

        parser = self.registry.resolve(doc.mime_type, doc.extension)
        if parser is None:
            raise AppException(code=ErrorCode.MANUAL_REVIEW, message="无可用解析器，进入人工处理", status_code=422)

        await self._set_stage(doc, task, DocumentStatus.CONVERTING)
        parsed = await self.registry.parse(str(original), doc.mime_type, doc.extension)
        if parsed.manual_review:
            raise AppException(code=ErrorCode.MANUAL_REVIEW, message="; ".join(parsed.warnings) or "需要人工处理", status_code=422)

        if doc.ocr_enabled and (parsed.needs_ocr or doc.extension in {".pdf"} and parsed.needs_ocr):
            await self._set_stage(doc, task, DocumentStatus.OCR)
            if doc.extension == ".pdf":
                parsed = await enrich_pdf_with_ocr(parsed, str(original), language=doc.language)

        if doc.ocr_enabled and doc.extension in {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".bmp",
            ".tif",
            ".tiff",
        }:
            await self._set_stage(doc, task, DocumentStatus.OCR)

        await self._set_stage(doc, task, DocumentStatus.NORMALIZING)
        package = await self.markdown.convert(
            parsed,
            content_hash=doc.content_hash,
            original_filename=doc.original_filename,
        )
        self.storage.clear_derived(doc.id)
        md_path, manifest_path, asset_paths = self.storage.write_markdown_package(
            doc.id,
            package.content_md,
            package.manifest,
            [(n, d) for n, d, _, _ in package.assets],
        )

        # Replace asset rows
        existing_assets = (
            await self.session.execute(
                select(DocumentAsset).where(DocumentAsset.document_id == doc.id)
            )
        ).scalars().all()
        for old in existing_assets:
            await self.session.delete(old)
        await self.session.flush()
        for (name, _data, mime, page_no), path in zip(package.assets, asset_paths, strict=False):
            self.session.add(
                DocumentAsset(
                    id=str(uuid.uuid4()),
                    document_id=doc.id,
                    filename=name,
                    relative_path=str(path.relative_to(self.storage.document_dir(doc.id))),
                    mime_type=mime,
                    size_bytes=path.stat().st_size,
                    page_no=page_no,
                )
            )

        doc.title = package.title or doc.title
        doc.parser_name = parsed.parser_name
        doc.parser_version = parsed.parser_version
        doc.page_count = parsed.page_count
        doc.markdown_path = str(md_path)
        doc.manifest_path = str(manifest_path)

        kb = await self._get_kb(doc.knowledge_base_id)
        await self._set_stage(doc, task, DocumentStatus.CHUNKING)
        chunks = await self.chunker.split(
            package.content_md,
            {
                "chunk_size": kb.chunk_size,
                "chunk_overlap": kb.chunk_overlap,
            },
        )

        await self._set_stage(doc, task, DocumentStatus.INDEXING)
        next_generation = await self._next_index_generation(doc.id)
        for chunk in chunks:
            embedding = self.indexer.embed_chunk(chunk)
            self.session.add(
                DocumentChunk(
                    id=str(uuid.uuid4()),
                    document_id=doc.id,
                    knowledge_base_id=doc.knowledge_base_id,
                    chunk_no=chunk.chunk_no,
                    section_no=chunk.section_no,
                    heading=chunk.heading,
                    page_no=chunk.page_no,
                    content=chunk.content,
                    char_start=chunk.char_start,
                    char_end=chunk.char_end,
                    token_estimate=chunk.token_estimate,
                    embedding_json=self.indexer.serialize_embedding(embedding),
                    index_generation=next_generation,
                    is_active=False,
                )
            )
        await self.session.flush()
        # Activate new generation only after full success; deactivate previous
        await self._activate_generation(doc.id, next_generation)

        doc.status = DocumentStatus.READY.value
        doc.is_active_index = True
        doc.error_code = None
        doc.error_message = None
        task.status = TaskStatus.SUCCEEDED.value
        task.stage = DocumentStatus.READY.value
        task.progress = 100
        task.finished_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def _set_stage(self, doc: Document, task: DocumentTask, stage: DocumentStatus) -> None:
        doc.status = stage.value
        task.stage = stage.value
        task.progress = float(STAGE_PROGRESS.get(stage.value, task.progress))
        await self.session.flush()

    async def _fail(
        self,
        doc: Document,
        task: DocumentTask,
        code: int,
        message: str,
        *,
        manual: bool = False,
    ) -> None:
        safe = message[:500]
        doc.error_code = code
        doc.error_message = safe
        doc.status = DocumentStatus.MANUAL_REVIEW.value if manual else DocumentStatus.FAILED.value
        task.error_code = code
        task.error_message = safe
        task.status = TaskStatus.MANUAL_REVIEW.value if manual else TaskStatus.FAILED.value
        task.stage = doc.status
        task.progress = 100
        task.finished_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def _find_by_hash(self, kb_id: str, content_hash: str) -> Document | None:
        stmt = (
            select(Document)
            .where(Document.knowledge_base_id == kb_id, Document.content_hash == content_hash)
            .order_by(Document.version.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def _latest_task(self, document_id: str) -> DocumentTask | None:
        stmt = (
            select(DocumentTask)
            .where(DocumentTask.document_id == document_id)
            .order_by(DocumentTask.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def _next_index_generation(self, document_id: str) -> int:
        stmt = select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        result = await self.session.execute(stmt)
        chunks = list(result.scalars())
        if not chunks:
            return 1
        return max(c.index_generation for c in chunks) + 1

    async def _activate_generation(self, document_id: str, generation: int) -> None:
        stmt = select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        result = await self.session.execute(stmt)
        for chunk in result.scalars():
            chunk.is_active = chunk.index_generation == generation
        await self.session.flush()

    async def _deactivate_index(self, document_id: str) -> None:
        stmt = select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        result = await self.session.execute(stmt)
        for chunk in result.scalars():
            chunk.is_active = False
        doc = await self.session.get(Document, document_id)
        if doc:
            doc.is_active_index = False
        await self.session.flush()
