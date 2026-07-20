"""知识库最小交付服务。"""

from __future__ import annotations

from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.common.models import KnowledgeBasePermission, User
from app.common.schemas import ErrorCode
from app.documents.models import Document, DocumentChunk, DocumentStatus
from app.documents.permissions import user_permission_codes
from app.knowledge.models import KnowledgeBase
from app.knowledge.schemas import (
    KnowledgeBaseCreate,
    KnowledgeBaseSummary,
    KnowledgeBaseUpdate,
)


def _is_admin(user: User) -> bool:
    permissions = user_permission_codes(user)
    return any(
        code in permissions
        for code in {
            "admin.knowledge_base.view",
            "admin.document.view",
            "admin.document.upload",
        }
    )


def _has_permission(user: User, code: str) -> bool:
    return code in user_permission_codes(user)


def _require_permission(user: User, code: str) -> None:
    if not _has_permission(user, code):
        raise ForbiddenException(message="当前账号没有管理知识库的权限")


async def _accessible_kb_ids(db: AsyncSession, user: User) -> set[str] | None:
    if _is_admin(user):
        return None

    role_ids = [role.id for role in user.roles if role.status == "active"]
    kb_ids: set[str] = set()

    user_rows = await db.execute(
        select(KnowledgeBasePermission.kb_id).where(
            KnowledgeBasePermission.subject_type == "user",
            KnowledgeBasePermission.subject_id == user.id,
        )
    )
    kb_ids.update(row[0] for row in user_rows.fetchall())

    if role_ids:
        role_rows = await db.execute(
            select(KnowledgeBasePermission.kb_id).where(
                KnowledgeBasePermission.subject_type == "role",
                KnowledgeBasePermission.subject_id.in_(role_ids),
            )
        )
        kb_ids.update(row[0] for row in role_rows.fetchall())

    return kb_ids


def _normalize_name(name: str) -> str:
    return " ".join(name.strip().split())


async def _ensure_name_available(
    db: AsyncSession, name: str, *, exclude_id: str | None = None
) -> None:
    stmt = select(KnowledgeBase.id).where(
        func.lower(func.trim(KnowledgeBase.name)) == name.lower()
    )
    if exclude_id is not None:
        stmt = stmt.where(KnowledgeBase.id != exclude_id)
    existing = (await db.execute(stmt.limit(1))).scalar_one_or_none()
    if existing is not None:
        raise ConflictException(
            code=ErrorCode.KB_ALREADY_EXISTS,
            message="知识库名称已存在，请换一个名称",
        )


async def _summaries(
    db: AsyncSession,
    knowledge_bases: list[KnowledgeBase],
) -> list[KnowledgeBaseSummary]:
    if not knowledge_bases:
        return []

    kb_ids = [item.id for item in knowledge_bases]
    doc_rows = await db.execute(
        select(
            Document.knowledge_base_id,
            func.count(Document.id),
            func.sum(case((Document.status == DocumentStatus.READY.value, 1), else_=0)),
        )
        .where(Document.knowledge_base_id.in_(kb_ids))
        .group_by(Document.knowledge_base_id)
    )
    chunk_rows = await db.execute(
        select(DocumentChunk.knowledge_base_id, func.count(DocumentChunk.id))
        .where(
            DocumentChunk.knowledge_base_id.in_(kb_ids),
            DocumentChunk.is_active.is_(True),
        )
        .group_by(DocumentChunk.knowledge_base_id)
    )

    doc_counts = {
        row[0]: {
            "document_count": int(row[1] or 0),
            "ready_document_count": int(row[2] or 0),
        }
        for row in doc_rows.fetchall()
    }
    chunk_counts = {row[0]: int(row[1] or 0) for row in chunk_rows.fetchall()}

    return [
        KnowledgeBaseSummary(
            id=item.id,
            name=item.name,
            description=item.description,
            status=item.status,
            chunk_size=item.chunk_size,
            chunk_overlap=item.chunk_overlap,
            document_count=doc_counts.get(item.id, {}).get("document_count", 0),
            ready_document_count=doc_counts.get(item.id, {}).get(
                "ready_document_count", 0
            ),
            chunk_count=chunk_counts.get(item.id, 0),
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in knowledge_bases
    ]


async def list_knowledge_bases(
    db: AsyncSession,
    user: User,
    *,
    page: int,
    page_size: int,
    active_only: bool = False,
) -> tuple[list[KnowledgeBaseSummary], int]:
    accessible = await _accessible_kb_ids(db, user)
    if accessible == set():
        return [], 0

    stmt = select(KnowledgeBase)
    if accessible is not None:
        stmt = stmt.where(KnowledgeBase.id.in_(accessible))
    if active_only:
        stmt = stmt.where(KnowledgeBase.status == "active")
    stmt = stmt.order_by(KnowledgeBase.updated_at.desc(), KnowledgeBase.created_at.desc())

    rows = await db.execute(stmt)
    all_items = list(rows.scalars())
    total = len(all_items)
    start = (page - 1) * page_size
    return await _summaries(db, all_items[start : start + page_size]), total


async def create_knowledge_base(
    db: AsyncSession,
    user: User,
    payload: KnowledgeBaseCreate,
) -> KnowledgeBaseSummary:
    _require_permission(user, "admin.knowledge_base.create")
    name = _normalize_name(payload.name)
    if name == "":
        raise ValidationException(message="知识库名称不能为空")
    await _ensure_name_available(db, name)

    item = KnowledgeBase(
        name=name,
        description=payload.description,
        chunk_size=payload.chunk_size,
        chunk_overlap=payload.chunk_overlap,
    )
    db.add(item)
    await db.flush()
    db.add(
        KnowledgeBasePermission(
            subject_type="user",
            subject_id=user.id,
            kb_id=item.id,
            access_level="admin",
        )
    )
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictException(
            code=ErrorCode.KB_ALREADY_EXISTS,
            message="知识库名称已存在，请换一个名称",
        ) from exc
    await db.refresh(item)
    return (await _summaries(db, [item]))[0]


async def update_knowledge_base(
    db: AsyncSession,
    user: User,
    kb_id: str,
    payload: KnowledgeBaseUpdate,
) -> KnowledgeBaseSummary:
    _require_permission(user, "admin.knowledge_base.edit")
    item = await db.get(KnowledgeBase, kb_id)
    if item is None:
        raise NotFoundException(message="知识库不存在")
    accessible = await _accessible_kb_ids(db, user)
    if accessible is not None and kb_id not in accessible:
        raise ForbiddenException(message="无权修改该知识库")

    update = payload.model_dump(exclude_unset=True)
    if "name" in update and update["name"] is not None:
        name = _normalize_name(str(update["name"]))
        if name == "":
            raise ValidationException(message="知识库名称不能为空")
        await _ensure_name_available(db, name, exclude_id=kb_id)
        update["name"] = name
    chunk_size = update.get("chunk_size")
    chunk_overlap = update.get("chunk_overlap")
    final_chunk_size = chunk_size if isinstance(chunk_size, int) else item.chunk_size
    final_chunk_overlap = (
        chunk_overlap if isinstance(chunk_overlap, int) else item.chunk_overlap
    )
    if final_chunk_overlap >= final_chunk_size:
        raise ValidationException(message="chunk_overlap 必须小于 chunk_size")
    for field, value in update.items():
        if value is not None:
            setattr(item, field, value)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictException(
            code=ErrorCode.KB_ALREADY_EXISTS,
            message="知识库名称已存在，请换一个名称",
        ) from exc
    await db.refresh(item)
    return (await _summaries(db, [item]))[0]
