"""模型管理 ORM 模型（提示词 01 §4.5）

由 Alembic 迁移创建表；此处仅声明 SQLAlchemy 模型以供 repository 读写。
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database import Base


class ModelProvider(Base):
    __tablename__ = "model_providers"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    base_url: Mapped[str] = mapped_column(String(512), nullable=False)
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Model(Base):
    __tablename__ = "models"
    __table_args__ = (Index("ix_models_provider_kind", "provider_code", "kind"),)

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False).with_variant(String(36), "sqlite"),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    provider_code: Mapped[str] = mapped_column(
        String(32), ForeignKey("model_providers.code", ondelete="RESTRICT"), nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSONB, default=dict)
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    dimensions: Mapped[int | None] = mapped_column(nullable=True)
    distance: Mapped[str | None] = mapped_column(String(16), nullable=True)
    top_n: Mapped[int | None] = mapped_column(nullable=True)
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())