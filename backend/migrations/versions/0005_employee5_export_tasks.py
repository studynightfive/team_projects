"""0005_employee5_export_tasks

Revision ID: 0005_employee5_export_tasks
Revises: 0004_employee5_conversations
Create Date: 2026-07-17

export_tasks 表（员工5 提示词 05 §4.8）
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_employee5_export_tasks"
down_revision: str | None = "0004_employee5_conversations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "export_tasks",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("format", sa.String(16), nullable=False),
        sa.Column(
            "document_ids",
            sa.dialects.postgresql.ARRAY(sa.dialects.postgresql.UUID(as_uuid=False)),
            nullable=False,
        ),
        sa.Column("options", sa.dialects.postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("progress", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("file_path", sa.String(1024), nullable=True),
        sa.Column("file_size", sa.Integer, nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_message", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_export_user_status", "export_tasks", ["user_id", "status"])
    op.create_index("ix_export_expires", "export_tasks", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_export_expires", table_name="export_tasks")
    op.drop_index("ix_export_user_status", table_name="export_tasks")
    op.drop_table("export_tasks")
