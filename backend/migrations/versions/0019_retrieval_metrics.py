"""Add structured retrieval metrics.

Revision ID: 0019_retrieval_metrics
Revises: 0018_personal_kb_chunk_strategy
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_retrieval_metrics"
down_revision: str | None = "0018_personal_kb_chunk_strategy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "retrieval_metrics",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("department_id", sa.String(36), nullable=True),
        sa.Column("knowledge_base_id", sa.String(36), nullable=True),
        sa.Column("event_type", sa.String(16), nullable=False),
        sa.Column(
            "hit_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "generated",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "cache_hit",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "took_ms",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "event_type IN ('search', 'answer')",
            name="ck_retrieval_metrics_event_type",
        ),
        sa.CheckConstraint(
            "hit_count >= 0",
            name="ck_retrieval_metrics_hit_count",
        ),
        sa.CheckConstraint(
            "took_ms >= 0",
            name="ck_retrieval_metrics_took_ms",
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "event_type",
            "request_id",
            name="uq_retrieval_metrics_event_request",
        ),
    )
    op.create_index(
        "ix_retrieval_metrics_department_created",
        "retrieval_metrics",
        ["department_id", "created_at"],
    )
    op.create_index(
        "ix_retrieval_metrics_event_created",
        "retrieval_metrics",
        ["event_type", "created_at"],
    )
    op.create_index(
        "ix_retrieval_metrics_user_created",
        "retrieval_metrics",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_retrieval_metrics_user_created",
        table_name="retrieval_metrics",
    )
    op.drop_index(
        "ix_retrieval_metrics_event_created",
        table_name="retrieval_metrics",
    )
    op.drop_index(
        "ix_retrieval_metrics_department_created",
        table_name="retrieval_metrics",
    )
    op.drop_table("retrieval_metrics")
