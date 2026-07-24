"""RAG 业务指标事实记录。"""

from __future__ import annotations

import uuid
from datetime import datetime

import structlog
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database import Base
from app.common.models import User

logger = structlog.get_logger()


class RetrievalMetric(Base):
    """一条已完成检索或回答的结构化事实。"""

    __tablename__ = "retrieval_metrics"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('search', 'answer')",
            name="ck_retrieval_metrics_event_type",
        ),
        CheckConstraint("hit_count >= 0", name="ck_retrieval_metrics_hit_count"),
        CheckConstraint("took_ms >= 0", name="ck_retrieval_metrics_took_ms"),
        UniqueConstraint(
            "event_type",
            "request_id",
            name="uq_retrieval_metrics_event_request",
        ),
        Index(
            "ix_retrieval_metrics_department_created",
            "department_id",
            "created_at",
        ),
        Index(
            "ix_retrieval_metrics_user_created",
            "user_id",
            "created_at",
        ),
        Index(
            "ix_retrieval_metrics_event_created",
            "event_type",
            "created_at",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    department_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    knowledge_base_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(16), nullable=False)
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cache_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    took_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    request_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


async def record_retrieval_metric(
    db: AsyncSession,
    *,
    user: User,
    event_type: str,
    request_id: str,
    knowledge_base_id: str | None,
    hit_count: int,
    generated: bool,
    cache_hit: bool,
    took_ms: int,
) -> None:
    """记录指标且不让观测数据故障阻断用户检索。"""

    try:
        async with db.begin_nested():
            db.add(
                RetrievalMetric(
                    user_id=user.id,
                    department_id=user.department_id,
                    knowledge_base_id=knowledge_base_id,
                    event_type=event_type,
                    hit_count=max(hit_count, 0),
                    generated=generated,
                    cache_hit=cache_hit,
                    took_ms=max(took_ms, 0),
                    request_id=request_id,
                )
            )
            await db.flush()
    except IntegrityError:
        logger.info(
            "retrieval_metric_duplicate",
            event_type=event_type,
            request_id=request_id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "retrieval_metric_write_failed",
            event_type=event_type,
            error_type=type(exc).__name__,
        )
