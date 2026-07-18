"""0003_employee5_chunks

Revision ID: 0003_employee5_chunks
Revises: 0002_employee5_models
Create Date: 2026-07-17

chunks 表（员工5 提示词 02 §4.6）
注意：doc_id / kb_id 的 FK 等员工3 / 员工4 完成 knowledge_bases 与 documents 表后加。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0003_employee5_chunks"
down_revision: str | None = "0002_employee5_models"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_table(
        "chunks",
        sa.Column("chunk_id", sa.String(64), primary_key=True),
        sa.Column("doc_id", sa.dialects.postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("kb_id", sa.dialects.postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("content", sa.Text, nullable=False, server_default=""),
        sa.Column("page", sa.Integer, nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("metadata", sa.dialects.postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_chunks_kb_id", "chunks", ["kb_id"])
    op.create_index("ix_chunks_doc_id", "chunks", ["doc_id"])
    op.execute("CREATE INDEX ix_chunks_tsv ON chunks USING gin (to_tsvector('simple', content))")
    op.execute("CREATE INDEX ix_chunks_metadata ON chunks USING gin (metadata)")
    op.execute(
        "CREATE INDEX ix_chunks_embedding ON chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chunks_embedding")
    op.execute("DROP INDEX IF EXISTS ix_chunks_metadata")
    op.execute("DROP INDEX IF EXISTS ix_chunks_tsv")
    op.drop_index("ix_chunks_doc_id", table_name="chunks")
    op.drop_index("ix_chunks_kb_id", table_name="chunks")
    op.drop_table("chunks")
