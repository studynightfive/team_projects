"""约束同一知识库中的活动文档名称唯一。

Revision ID: 0021_unique_document_names
Revises: 0020_document_recycle_bin
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0021_unique_document_names"
down_revision: str | None = "0020_document_recycle_bin"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 先为历史重复记录追加稳定 ID 标识，确保创建唯一索引时不丢弃任何文档。
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                row_number() OVER (
                    PARTITION BY knowledge_base_id, lower(btrim(title))
                    ORDER BY created_at, id
                ) AS duplicate_number
            FROM documents
            WHERE deleted_at IS NULL
        )
        UPDATE documents AS document
        SET
            title = document.title || ' [' || left(document.id, 8) || ']',
            original_filename =
                regexp_replace(document.original_filename, '(\\.[^.]+)$', '')
                || ' [' || left(document.id, 8) || ']'
                || coalesce(substring(document.original_filename FROM '(\\.[^.]+)$'), '')
        FROM ranked
        WHERE document.id = ranked.id
          AND ranked.duplicate_number > 1
        """
    )
    # 软删除文档不占用名称，恢复时由服务层重新检查并生成可读编号。
    op.execute(
        """
        CREATE UNIQUE INDEX uq_documents_active_kb_title
        ON documents (knowledge_base_id, lower(btrim(title)))
        WHERE deleted_at IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("uq_documents_active_kb_title", table_name="documents")
