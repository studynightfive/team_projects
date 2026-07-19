"""add qwen embedding vector to document chunks

Revision ID: 0011_qwen_embedding_vector
Revises: 0010_notifications
Create Date: 2026-07-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0011_qwen_embedding_vector"
down_revision = "0010_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "document_chunks",
        sa.Column("embedding_vector", Vector(1024), nullable=True),
    )
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding_vector "
        "ON document_chunks USING hnsw (embedding_vector vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_vector")
    op.drop_column("document_chunks", "embedding_vector")
