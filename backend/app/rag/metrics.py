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
from app.knowledge.models import KnowledgeBase

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
        Index(
            "ix_retrieval_metrics_product_created",
            "department_id",
            "primary_product_id",
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
    primary_product_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )
    primary_product_name: Mapped[str | None] = mapped_column(
        String(500),
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
    primary_product_id: str | None = None,
    primary_product_name: str | None = None,
) -> None:
    """记录指标且不让观测数据故障阻断用户检索。"""

    product_id = (primary_product_id or "").strip()[:36] or None
    product_name = (primary_product_name or "").strip()[:500] or None
    if product_id is None or product_name is None:
        # 商品标识和展示名称必须成对出现，避免生成无法解释的运营数据。
        product_id = None
        product_name = None

    try:
        # 运营指标描述的是被查询知识的归属，不是发起查询账号的组织归属。
        knowledge_base = (
            await db.get(KnowledgeBase, knowledge_base_id)
            if knowledge_base_id is not None
            else None
        )
        department_id = (
            knowledge_base.department_id if knowledge_base is not None else None
        )
        async with db.begin_nested():
            db.add(
                RetrievalMetric(
                    user_id=user.id,
                    department_id=department_id,
                    knowledge_base_id=knowledge_base_id,
                    primary_product_id=product_id,
                    primary_product_name=product_name,
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
