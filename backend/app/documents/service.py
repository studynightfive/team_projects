"""Document upload, processing pipeline, retry and query services."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import Settings
from app.common.config import settings as app_settings
from app.common.exceptions import AppException, ForbiddenException, NotFoundException
from app.common.models import User
from app.common.schemas import ErrorCode
from app.documents.chunking import Chunk, Chunker
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
    AdminDocumentItem,
    AdminTaskItem,
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
from app.models import service as model_service
from app.models.providers.openai import build_provider
from app.models.security import decrypt_api_key
from app.parsers.mime import detect_file
from app.parsers.pdf import enrich_pdf_with_ocr
from app.parsers.registry import get_parser_registry
from app.worker.queue import enqueue_document_task, enqueue_document_tasks


def get_settings() -> Settings:
    return app_settings


def new_request_id() -> str:
    return str(uuid.uuid4())


logger = structlog.get_logger()

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
        condition = Document.knowledge_base_id == kb_id
        total = (
            await self.session.execute(
                select(func.count()).select_from(Document).where(condition)
            )
        ).scalar() or 0
        offset = (page - 1) * page_size
        result = await self.session.execute(
            select(Document)
            .where(condition)
            .order_by(Document.updated_at.desc(), Document.id.desc())
            .offset(offset)
            .limit(page_size)
        )
        items = list(result.scalars())
        return [DocumentSummary.model_validate(d) for d in items], total

    async def list_admin_documents(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        status: str | None = None,
    ) -> tuple[list[AdminDocumentItem], int]:
        stmt = select(Document, KnowledgeBase.name).join(
            KnowledgeBase, KnowledgeBase.id == Document.knowledge_base_id
        )
        if search:
            keyword = f"%{search}%"
            stmt = stmt.where(
                Document.title.ilike(keyword)
                | Document.original_filename.ilike(keyword)
                | KnowledgeBase.name.ilike(keyword)
            )
        if status:
            stmt = stmt.where(Document.status == status)

        total = (
            await self.session.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar() or 0
        offset = (page - 1) * page_size
        rows = await self.session.execute(
            stmt.order_by(Document.updated_at.desc()).offset(offset).limit(page_size)
        )
        items: list[AdminDocumentItem] = []
        for document, kb_name in rows.all():
            data = DocumentSummary.model_validate(document).model_dump()
            items.append(AdminDocumentItem(**data, knowledge_base_name=kb_name))
        return items, total

    async def list_admin_tasks(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        status: str | None = None,
    ) -> tuple[list[AdminTaskItem], int]:
        stmt = (
            select(DocumentTask, Document, KnowledgeBase.name)
            .join(Document, Document.id == DocumentTask.document_id)
            .join(KnowledgeBase, KnowledgeBase.id == Document.knowledge_base_id)
        )
        if search:
            keyword = f"%{search}%"
            stmt = stmt.where(
                Document.title.ilike(keyword)
                | DocumentTask.stage.ilike(keyword)
                | KnowledgeBase.name.ilike(keyword)
            )
        if status:
            stmt = stmt.where(DocumentTask.status == status)

        total = (
            await self.session.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar() or 0
        offset = (page - 1) * page_size
        rows = await self.session.execute(
            stmt.order_by(DocumentTask.created_at.desc()).offset(offset).limit(page_size)
        )
        items: list[AdminTaskItem] = []
        for task, document, kb_name in rows.all():
            data = TaskResponse.from_orm_task(task).model_dump()
            items.append(
                AdminTaskItem(
                    **data,
                    document_id=document.id,
                    document_title=document.title,
                    knowledge_base_id=document.knowledge_base_id,
                    knowledge_base_name=kb_name,
                    started_at=task.started_at,
                )
            )
        return items, total

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
        require_any_permission(
            user,
            "admin.task.view",
            "admin.document.view",
            "document.view",
            "admin.document.upload",
            "document.upload",
        )
        return TaskResponse.from_orm_task(task)

    async def upload(
        self,
        user: User,
        kb_id: str,
        files: list[tuple[str, bytes]],
        options: UploadOptions,
    ) -> UploadResponse:
        require_any_permission(
            user,
            "admin.document.upload",
            "document.upload",
        )
        if not await user_can_access_kb(self.session, user, str(kb_id)):
            raise ForbiddenException(message="无权访问该知识库")
        await self._get_kb(kb_id)

        if not files:
            raise AppException(code=ErrorCode.UPLOAD_INVALID, message="未上传文件", status_code=400)
        if len(files) > self.settings.max_upload_files:
            raise AppException(code=ErrorCode.UPLOAD_INVALID, message=f"单次最多上传 {self.settings.max_upload_files} 个文件", status_code=400)

        items: list[UploadResultItem] = []
        created_document_ids: set[str] = set()
        replacement_backups: dict[str, Path] = {}
        try:
            for filename, data in files:
                items.append(
                    await self._upload_one(
                        user,
                        kb_id,
                        filename,
                        data,
                        options,
                        created_document_ids=created_document_ids,
                        replacement_backups=replacement_backups,
                    )
                )
            await self.session.commit()
        except Exception:
            try:
                await self.session.rollback()
            finally:
                for document_id in created_document_ids:
                    self.storage.delete_document(document_id)
                for document_id, backup in replacement_backups.items():
                    self.storage.restore_document(document_id, backup)
            raise

        for document_id, backup in replacement_backups.items():
            try:
                self.storage.discard_backup(backup)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "document_backup_cleanup_failed",
                    document_id=document_id,
                    error_type=type(exc).__name__,
                )
        if not self.settings.worker_inline:
            await self._enqueue_items(items)
        return UploadResponse(items=items)

    async def _upload_one(
        self,
        user: User,
        kb_id: str,
        filename: str,
        data: bytes,
        options: UploadOptions,
        *,
        created_document_ids: set[str],
        replacement_backups: dict[str, Path],
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
            if existing.id not in replacement_backups:
                replacement_backups[existing.id] = self.storage.backup_document(existing.id)
            await self._deactivate_index(existing.id)
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
            document_id = str(uuid.uuid4())
            created_document_ids.add(document_id)
            document = Document(
                id=document_id,
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
        idempotency_key = f"{document.id}:{content_hash}:v{document.version}"
        if existing and options.duplicate_policy == DuplicatePolicy.REPLACE:
            idempotency_key = f"{document.id}:replace:{request_id}"
        task = DocumentTask(
            id=str(uuid.uuid4()),
            document_id=document.id,
            task_type="document_convert",
            status=TaskStatus.QUEUED.value,
            stage=DocumentStatus.UPLOADED.value,
            progress=STAGE_PROGRESS[DocumentStatus.UPLOADED.value],
            retry_count=0,
            idempotency_key=idempotency_key,
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
        if not self.settings.worker_inline:
            await self._enqueue_or_fail(doc.id, task.id)
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
        self.storage.delete_document(doc.id)

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
            logger.warning(
                "document_processing_failed",
                document_id=document_id,
                task_id=task_id,
                error_type=type(exc).__name__,
            )
            await self._fail(doc, task, ErrorCode.PARSE_FAILED, "文档处理失败")

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
        embedding_vectors = await self._embed_chunks_with_configured_model(chunks)
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
                    embedding_vector=embedding_vectors.get(chunk.chunk_no),
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

    async def _embed_chunks_with_configured_model(
        self,
        chunks: list[Chunk],
    ) -> dict[int, list[float]]:
        models = await model_service.list_models(self.session, kind="embedding")
        model = next(
            (
                item
                for item in models
                if item.enabled and item.model_name == self.settings.qwen_embedding_model
            ),
            None,
        )
        if model is None or not model.api_key_encrypted:
            return {}

        provider = await model_service.get_provider(self.session, model.provider_code)
        if provider is None or not provider.enabled:
            return {}

        api_key = decrypt_api_key(model.api_key_encrypted)
        provider_client = build_provider(provider.code, provider.base_url, api_key)
        vectors: dict[int, list[float]] = {}
        try:
            for start in range(0, len(chunks), 16):
                batch = chunks[start : start + 16]
                embeddings = await provider_client.embed(
                    model_name=model.model_name,
                    inputs=[chunk.content for chunk in batch],
                )
                for chunk, embedding in zip(batch, embeddings, strict=False):
                    if len(embedding) == self.settings.qwen_embedding_dimensions:
                        vectors[chunk.chunk_no] = embedding
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "qwen_embedding_failed_fallback_to_stub",
                error_type=type(exc).__name__,
            )
            return {}
        return vectors

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

    async def _enqueue_items(self, items: list[UploadResultItem]) -> None:
        pending = [
            (item.document.id, item.task_id)
            for item in items
            if not item.skipped
        ]
        try:
            failures = await enqueue_document_tasks(pending, self.settings.redis_url)
        except Exception as exc:
            failures = {task_id: type(exc).__name__ for _, task_id in pending}
        for item in items:
            error_type = failures.get(item.task_id)
            if error_type is not None:
                await self._mark_enqueue_failed(item.document.id, item.task_id)
                logger.warning(
                    "document_enqueue_failed",
                    task_id=item.task_id,
                    error_type=error_type,
                )
        if failures:
            await self.session.commit()
            raise AppException(
                code=ErrorCode.CONVERSION_FAILED,
                message="任务队列暂不可用，请稍后重试",
                status_code=503,
            )

    async def _enqueue_or_fail(self, document_id: str, task_id: str) -> None:
        try:
            await enqueue_document_task(document_id, task_id, self.settings.redis_url)
        except Exception as exc:
            await self._mark_enqueue_failed(document_id, task_id)
            await self.session.commit()
            logger.warning(
                "document_enqueue_failed",
                task_id=task_id,
                error_type=type(exc).__name__,
            )
            raise AppException(
                code=ErrorCode.CONVERSION_FAILED,
                message="任务队列暂不可用，请稍后重试",
                status_code=503,
            ) from exc

    async def _mark_enqueue_failed(self, document_id: str, task_id: str) -> None:
        document = await self.session.get(Document, document_id)
        task = await self.session.get(DocumentTask, task_id)
        if document is not None and task is not None:
            await self._fail(
                document,
                task,
                ErrorCode.CONVERSION_FAILED,
                "任务未能加入处理队列",
            )

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
