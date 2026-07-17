"""chunks ORM 模型（提示词 02 §4.6）"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, FLOAT, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database import Base


class Chunk(Base):
    """chunks 表：员工4 documents 输出 schema（本期员工4 未就绪时，使用 fixture）。"""

    __tablename__ = "chunks"
    __table_args__ = (
        Index("ix_chunks_kb_id", "kb_id"),
        Index("ix_chunks_doc_id", "doc_id"),
    )

    chunk_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    # TODO 员工4 完成 documents 表后，把 doc_id 改为 UUID + FK
    doc_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False).with_variant(String(36), "sqlite"), nullable=False
    )
    # TODO 员工3 完成 knowledge_bases 表后，把 kb_id 改为 UUID + FK
    kb_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False).with_variant(String(36), "sqlite"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(ARRAY(FLOAT), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
