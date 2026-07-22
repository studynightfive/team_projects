# 知识库模型（员工 4 文档处理依赖；知识库 CRUD 仍由知识模块后续完善）

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database import Base
from app.departments.models import DEFAULT_DEPARTMENT_ID


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"
    __table_args__ = (
        CheckConstraint(
            "(kind = 'enterprise' AND owner_user_id IS NULL) OR "
            "(kind = 'personal' AND owner_user_id IS NOT NULL)",
            name="ck_knowledge_bases_kind_owner",
        ),
        Index("ix_knowledge_bases_department_id", "department_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    department_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("departments.id", ondelete="RESTRICT"),
        nullable=False,
        default=DEFAULT_DEPARTMENT_ID,
    )
    kind: Mapped[str] = mapped_column(String(16), default="enterprise", nullable=False)
    owner_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    chunk_size: Mapped[int] = mapped_column(Integer, default=800, nullable=False)
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=120, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


Index(
    "uq_knowledge_bases_enterprise_department_name",
    KnowledgeBase.department_id,
    func.lower(func.btrim(KnowledgeBase.name)),
    unique=True,
    postgresql_where=text("kind = 'enterprise'"),
)
Index(
    "uq_knowledge_bases_personal_owner",
    KnowledgeBase.owner_user_id,
    unique=True,
    postgresql_where=text("kind = 'personal'"),
)
