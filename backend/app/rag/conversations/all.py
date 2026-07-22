"""会话管理（提示词 04）—— schemas + repository + service + api 单文件版

为减少文件 IO 次数，会话、消息、回答版本管理与路由集中在此文件。
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Literal, cast

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.auth.dependencies import get_current_user, require_any_permission, require_permission
from app.common.database import Base, get_db
from app.common.exceptions import ForbiddenException, NotFoundException, ValidationException
from app.common.models import User
from app.common.schemas import APIResponse, PaginatedData
from app.documents.permissions import user_can_access_kb
from app.knowledge.models import KnowledgeBase
from app.rag._shared.audit_helper import audit
from app.rag.guard import ensure_safe_query


# ============================================================
# ORM 模型
# ============================================================
class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conv_user_updated", "user_id", "updated_at"),
        Index("ix_conv_user_pinned", "user_id", "is_pinned"),
        Index("ix_conv_deleted", "deleted_at"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False).with_variant(String(36), "sqlite"),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    kb_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("knowledge_bases.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_msg_conv_created", "conversation_id", "created_at"),
        Index("ix_msg_parent", "parent_message_id"),
        Index("ix_msg_conv_latest", "conversation_id", "is_latest"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False).with_variant(String(36), "sqlite"),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    conversation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False).with_variant(String(36), "sqlite"),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    citations: Mapped[list[dict[str, object]]] = mapped_column(JSONB, default=list)
    answer_version: Mapped[int] = mapped_column(Integer, default=1)
    is_latest: Mapped[bool] = mapped_column(Boolean, default=True)
    parent_message_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False).with_variant(String(36), "sqlite"),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    finish_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    usage: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# Schemas
# ============================================================
Role = Literal["system", "user", "assistant", "tool"]


class ConversationCreate(BaseModel):
    kb_id: str
    title: str | None = Field(default=None, max_length=200)
    first_question: str = Field(min_length=1, max_length=4000)


class ConversationUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    is_pinned: bool | None = None
    is_archived: bool | None = None


class ConversationResponse(BaseModel):
    id: str
    user_id: str
    kb_id: str
    title: str
    is_pinned: bool
    is_archived: bool
    message_count: int
    last_message_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}


class Citation(BaseModel):
    doc_id: str
    chunk_id: str
    page: int | None = None
    score: float | None = None
    text: str | None = None


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: Role
    content: str
    citations: list[Citation] = Field(default_factory=list)
    answer_version: int = 1
    is_latest: bool = True
    parent_message_id: str | None = None
    finish_reason: str | None = None
    usage: dict[str, object] = Field(default_factory=dict)
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


# ============================================================
# 业务逻辑
# ============================================================
async def list_conversations(
    db: AsyncSession,
    *,
    user_id: str,
    page: int,
    page_size: int,
    query_text: str | None = None,
    include_archived: bool = False,
) -> tuple[Sequence[Conversation], int]:
    base = select(Conversation).where(
        Conversation.user_id == user_id, Conversation.deleted_at.is_(None)
    )
    if not include_archived:
        base = base.where(Conversation.is_archived.is_(False))
    if query_text:
        like = f"%{query_text}%"
        base = base.where(
            (Conversation.title.ilike(like))
            | Conversation.id.in_(
                select(Message.conversation_id).where(Message.content.ilike(like)).distinct()
            )
        )
    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    offset = (page - 1) * page_size
    res = await db.execute(
        base.order_by(Conversation.is_pinned.desc(), Conversation.updated_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    return res.scalars().all(), total


async def create_conversation(
    db: AsyncSession, *, user_id: str, payload: ConversationCreate
) -> tuple[Conversation, Message]:
    conv = Conversation(user_id=user_id, kb_id=payload.kb_id, title=payload.title or "")
    db.add(conv)
    await db.flush()  # 取 id
    first_msg = Message(
        conversation_id=conv.id, role="user", content=payload.first_question, is_latest=True
    )
    db.add(first_msg)
    conv.message_count = 1
    conv.last_message_at = func.now()
    return conv, first_msg


async def get_conversation(db: AsyncSession, *, conv_id: str, user_id: str) -> Conversation:
    conv = await db.get(Conversation, conv_id)
    if conv is None or conv.deleted_at is not None:
        raise NotFoundException()
    if conv.user_id != user_id:
        raise ForbiddenException(message="无权访问此会话")
    return conv


async def update_conversation(
    db: AsyncSession, *, conv: Conversation, payload: ConversationUpdate
) -> Conversation:
    if payload.title is not None:
        conv.title = payload.title
    if payload.is_pinned is not None:
        conv.is_pinned = payload.is_pinned
    if payload.is_archived is not None:
        conv.is_archived = payload.is_archived
    return conv


async def soft_delete_conversation(db: AsyncSession, *, conv: Conversation) -> None:
    # SELECT FOR UPDATE 由路由层 select() 加 with_for_update()
    conv.deleted_at = datetime.now(timezone.utc)


async def list_messages(
    db: AsyncSession,
    *,
    conv_id: str,
    page: int,
    page_size: int,
    only_latest: bool = True,
) -> tuple[Sequence[Message], int, bool]:
    q = select(Message).where(Message.conversation_id == conv_id, Message.deleted_at.is_(None))
    if only_latest:
        q = q.where(Message.is_latest.is_(True))
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
    offset = (page - 1) * page_size
    res = await db.execute(q.order_by(Message.created_at.asc()).offset(offset).limit(page_size + 1))
    rows = list(res.scalars().all())
    has_more = len(rows) > page_size
    return rows[:page_size], total, has_more


async def append_message(
    db: AsyncSession,
    *,
    conv_id: str,
    role: Role,
    content: str,
    citations: list[dict[str, object]] | None = None,
    parent_message_id: str | None = None,
    finish_reason: str | None = None,
    usage: dict[str, object] | None = None,
) -> Message:
    msg = Message(
        conversation_id=conv_id,
        role=role,
        content=content,
        citations=citations or [],
        parent_message_id=parent_message_id,
        finish_reason=finish_reason,
        usage=usage or {},
        is_latest=True,
    )
    db.add(msg)
    conv = await db.get(Conversation, conv_id)
    if conv is not None:
        conv.message_count = (conv.message_count or 0) + 1
        conv.last_message_at = datetime.now(timezone.utc)
    return msg


async def regenerate_answer(
    db: AsyncSession,
    *,
    parent_message_id: str,
) -> Message:
    """把 parent_message 的 is_latest 标 false，插入新版本。"""
    parent = await db.get(Message, parent_message_id)
    if parent is None:
        raise NotFoundException()
    parent.is_latest = False
    new_msg = Message(
        conversation_id=parent.conversation_id,
        role=parent.role,
        content="",
        parent_message_id=parent.id,
        answer_version=parent.answer_version + 1,
        is_latest=True,
    )
    db.add(new_msg)
    return new_msg


# ============================================================
# 路由
# ============================================================
router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


@router.get("")
async def list_conversations_endpoint(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    query_text: str | None = Query(None, alias="q"),
    include_archived: bool = Query(False),
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_any_permission("conversation:read", "conversation.view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    convs, total = await list_conversations(
        db,
        user_id=user.id,
        page=page,
        page_size=page_size,
        query_text=query_text,
        include_archived=include_archived,
    )
    items = [ConversationResponse.model_validate(c).model_dump() for c in convs]
    return APIResponse(
        data=PaginatedData(items=items, page=page, page_size=page_size, total=total).model_dump()
    ).model_dump()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_conversation_endpoint(
    request: Request,
    payload: ConversationCreate,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_any_permission("conversation:write", "chat.use")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    await ensure_safe_query(payload.first_question)
    knowledge_base = await db.get(KnowledgeBase, payload.kb_id)
    if knowledge_base is None:
        raise NotFoundException(message="知识库不存在")
    if not await user_can_access_kb(db, user, payload.kb_id):
        raise ForbiddenException(message="无权访问该知识库")
    conv, _first = await create_conversation(db, user_id=user.id, payload=payload)
    await db.commit()
    await audit(
        db,
        action="conversation_create",
        user_id=user.id,
        resource_type="conversation",
        resource_id=conv.id,
        request=request,
    )
    await db.commit()
    return APIResponse(data=ConversationResponse.model_validate(conv).model_dump()).model_dump()


@router.patch("/{conversation_id}")
async def patch_conversation_endpoint(
    conversation_id: str,
    request: Request,
    payload: ConversationUpdate,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_any_permission("conversation:write", "chat.use")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    conv = await get_conversation(db, conv_id=conversation_id, user_id=user.id)
    conv = await update_conversation(db, conv=conv, payload=payload)
    await db.commit()
    await audit(
        db,
        action="conversation_patch",
        user_id=user.id,
        resource_id=conversation_id,
        request=request,
    )
    await db.commit()
    return APIResponse(data=ConversationResponse.model_validate(conv).model_dump()).model_dump()


@router.delete("/{conversation_id}")
async def delete_conversation_endpoint(
    conversation_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("conversation:delete")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    # SELECT FOR UPDATE 保证并发删除原子化
    res = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id).with_for_update()
    )
    conv = res.scalar_one_or_none()
    if conv is None or conv.deleted_at is not None:
        raise NotFoundException()
    if conv.user_id != user.id:
        raise ForbiddenException()
    await soft_delete_conversation(db, conv=conv)
    await db.commit()
    await audit(
        db,
        action="conversation_delete",
        user_id=user.id,
        resource_id=conversation_id,
        request=request,
    )
    await db.commit()
    return APIResponse().model_dump()


@router.get("/{conversation_id}/messages")
async def list_messages_endpoint(
    conversation_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    only_latest: bool = Query(True),
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_any_permission("conversation:read", "conversation.view")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    conv = await get_conversation(db, conv_id=conversation_id, user_id=user.id)
    msgs, total, has_more = await list_messages(
        db,
        conv_id=conv.id,
        page=page,
        page_size=page_size,
        only_latest=only_latest,
    )
    items = [MessageResponse.model_validate(m).model_dump() for m in msgs]
    return APIResponse(
        data={
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "has_more": has_more,
        }
    ).model_dump()


@router.post("/{conversation_id}/messages")
async def append_message_endpoint(
    conversation_id: str,
    request: Request,
    payload: dict[str, object],
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_any_permission("conversation:write", "chat.use")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    conv = await get_conversation(db, conv_id=conversation_id, user_id=user.id)
    role_value = payload.get("role", "user")
    content = payload.get("content", "")
    if role_value not in ("user", "system", "tool"):
        raise ValidationException(message="role 必须为 user / system / tool")
    if not isinstance(content, str):
        raise ValidationException(message="content 必须为字符串")
    role = cast(Role, role_value)
    if role == "user":
        await ensure_safe_query(content)
    msg = await append_message(db, conv_id=conv.id, role=role, content=content)
    await db.commit()
    return APIResponse(data=MessageResponse.model_validate(msg).model_dump()).model_dump()
