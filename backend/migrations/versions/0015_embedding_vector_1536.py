"""将 document_chunks.embedding_vector 从 1024 维升级为 1536（text-embedding-v2）。

Revision ID: 0015_embedding_vector_1536
Revises: 0014_conversation_integrity
Create Date: 2026-07-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0015_embedding_vector_1536"
down_revision: str | None = "0014_conversation_integrity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_vector")
    # 维度变更无法无损转换，清空旧向量后重建列
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding_vector")
    op.add_column(
        "document_chunks",
        sa.Column("embedding_vector", Vector(1536), nullable=True),
    )
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding_vector "
        "ON document_chunks USING hnsw (embedding_vector vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_vector")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding_vector")
    op.add_column(
        "document_chunks",
        sa.Column("embedding_vector", Vector(1024), nullable=True),
    )
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding_vector "
        "ON document_chunks USING hnsw (embedding_vector vector_cosine_ops)"
    )
