"""0006_employee5_retrieval_tests

Revision ID: 0006_employee5_retrieval_tests
Revises: 0005_employee5_export_tasks
Create Date: 2026-07-17

retrieval_test_datasets + retrieval_test_runs 表（员工5 提示词 06 §4.6）
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_employee5_retrieval_tests"
down_revision: str | None = "0005_employee5_export_tasks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "retrieval_test_datasets",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("kb_id", sa.dialects.postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("queries", sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column(
            "created_by",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_test_dataset_kb", "retrieval_test_datasets", ["kb_id"])

    op.create_table(
        "retrieval_test_runs",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "dataset_id",
            sa.dialects.postgresql.UUID(as_uuid=False),
            sa.ForeignKey("retrieval_test_datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("config", sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column("config_hash", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("progress", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("total", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("metrics", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("per_query", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("error_message", sa.String(512), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_test_run_dataset", "retrieval_test_runs", ["dataset_id"])
    op.create_index("ix_test_run_hash", "retrieval_test_runs", ["dataset_id", "config_hash"])
    op.create_index("ix_test_run_status", "retrieval_test_runs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_test_run_status", table_name="retrieval_test_runs")
    op.drop_index("ix_test_run_hash", table_name="retrieval_test_runs")
    op.drop_index("ix_test_run_dataset", table_name="retrieval_test_runs")
    op.drop_table("retrieval_test_runs")
    op.drop_index("ix_test_dataset_kb", table_name="retrieval_test_datasets")
    op.drop_table("retrieval_test_datasets")
