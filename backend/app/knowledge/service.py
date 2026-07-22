"""知识库最小交付服务。"""

from __future__ import annotations

from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.common.models import KnowledgeBasePermission, User
from app.common.organization import can_manage_department, is_super_admin
from app.common.schemas import ErrorCode
from app.departments.models import Department
from app.documents.models import Document, DocumentChunk, DocumentStatus
from app.knowledge.models import KnowledgeBase
from app.knowledge.schemas import (
    KnowledgeBaseCreate,
    KnowledgeBaseSummary,
    KnowledgeBaseUpdate,
)


async def _accessible_kb_ids(db: AsyncSession, user: User) -> set[str] | None:
    clauses = [KnowledgeBase.owner_user_id == user.id]
    if is_super_admin(user):
        clauses.append(KnowledgeBase.kind == "enterprise")
    elif user.department_id is not None:
        clauses.append(
            (KnowledgeBase.kind == "enterprise")
            & (KnowledgeBase.department_id == user.department_id)
        )
    rows = await db.execute(
        select(KnowledgeBase.id).where(or_(*clauses))
    )
    return {row[0] for row in rows.fetchall()}


async def ensure_personal_knowledge_base(
    db: AsyncSession, user: User
) -> KnowledgeBase:
    existing = (
        await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.kind == "personal",
                KnowledgeBase.owner_user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    department_id = user.department_id or "00000000-0000-0000-0000-000000000001"
    if await db.get(Department, department_id) is None:
        raise ValidationException(message="创建个人知识库前必须先分配有效部门")
    item = KnowledgeBase(
        name=f"{user.display_name}的个人知识库",
        description="用于存放个人文档，仅本人可访问",
        department_id=department_id,
        kind="personal",
        owner_user_id=user.id,
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
    await db.flush()
    return item


def _normalize_name(name: str) -> str:
    return " ".join(name.strip().split())


async def _ensure_name_available(
    db: AsyncSession,
    name: str,
    *,
    department_id: str,
    exclude_id: str | None = None,
) -> None:
    stmt = select(KnowledgeBase.id).where(
        KnowledgeBase.kind == "enterprise",
        KnowledgeBase.department_id == department_id,
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
    department_ids = {item.department_id for item in knowledge_bases}
    department_names = {
        row[0]: row[1]
        for row in (
            await db.execute(
                select(Department.id, Department.name).where(
                    Department.id.in_(department_ids)
                )
            )
        ).all()
    }
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
            department_id=item.department_id,
            department_name=department_names.get(item.department_id, "未知部门"),
            kind=item.kind,
            owner_user_id=item.owner_user_id,
            status=item.status,
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
    department_id = payload.department_id or user.department_id
    if department_id is None:
        raise ValidationException(message="创建知识库前必须先分配部门")
    department = await db.get(Department, department_id)
    if department is None:
        raise NotFoundException(message="部门不存在")
    if not await can_manage_department(db, user, department_id):
        raise ForbiddenException(message="只有超级管理员或本部门管理员可以创建知识库")
    name = _normalize_name(payload.name)
    if name == "":
        raise ValidationException(message="知识库名称不能为空")
    await _ensure_name_available(db, name, department_id=department_id)

    item = KnowledgeBase(
        name=name,
        description=payload.description,
        department_id=department_id,
        kind="enterprise",
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
    item = await db.get(KnowledgeBase, kb_id)
    if item is None:
        raise NotFoundException(message="知识库不存在")
    if item.kind == "personal":
        raise ForbiddenException(message="个人知识库不支持在管理端修改")
    if not await can_manage_department(db, user, item.department_id):
        raise ForbiddenException(message="无权修改该知识库")

    update = payload.model_dump(exclude_unset=True)
    if "name" in update and update["name"] is not None:
        name = _normalize_name(str(update["name"]))
        if name == "":
            raise ValidationException(message="知识库名称不能为空")
        target_department_id = str(update.get("department_id") or item.department_id)
        await _ensure_name_available(
            db,
            name,
            department_id=target_department_id,
            exclude_id=kb_id,
        )
        update["name"] = name
    if "department_id" in update and update["department_id"] is not None:
        target_department_id = str(update["department_id"])
        if not is_super_admin(user):
            raise ForbiddenException(message="只有超级管理员可以调整知识库所属部门")
        if await db.get(Department, target_department_id) is None:
            raise NotFoundException(message="部门不存在")
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
