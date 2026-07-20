"""Favorite ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database import Base


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (
        Index("ix_favorites_user_saved", "user_id", "saved_at"),
        Index("ix_favorites_user_type", "user_id", "type"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False).with_variant(String(36), "sqlite"),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(24), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_payload: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
