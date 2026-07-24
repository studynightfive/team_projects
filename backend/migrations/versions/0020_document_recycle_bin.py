"""Add document recycle-bin metadata.

Revision ID: 0020_document_recycle_bin
Revises: 0019_retrieval_metrics
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_document_recycle_bin"
down_revision: str | None = "0019_retrieval_metrics"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("deleted_by", sa.String(36), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("purge_after", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_documents_deleted_at",
        "documents",
        ["deleted_at"],
    )
    op.create_index(
        "ix_documents_purge_after",
        "documents",
        ["purge_after"],
    )


def downgrade() -> None:
    op.drop_index("ix_documents_purge_after", table_name="documents")
    op.drop_index("ix_documents_deleted_at", table_name="documents")
    op.drop_column("documents", "purge_after")
    op.drop_column("documents", "deleted_by")
    op.drop_column("documents", "deleted_at")
