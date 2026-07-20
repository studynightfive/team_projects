"""align database constraints with ORM models

Revision ID: 0012_schema_consistency
Revises: 0011_qwen_embedding_vector
Create Date: 2026-07-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0012_schema_consistency"
down_revision = "0011_qwen_embedding_vector"
branch_labels = None
depends_on = None

_TIMESTAMP_COLUMNS = (
    ("audit_logs", "created_at"),
    ("chunks", "created_at"),
    ("conversations", "created_at"),
    ("conversations", "updated_at"),
    ("document_assets", "created_at"),
    ("document_chunks", "created_at"),
    ("document_tasks", "created_at"),
    ("documents", "created_at"),
    ("documents", "updated_at"),
    ("export_tasks", "created_at"),
    ("favorites", "saved_at"),
    ("favorites", "updated_at"),
    ("knowledge_base_permissions", "created_at"),
    ("knowledge_bases", "created_at"),
    ("knowledge_bases", "updated_at"),
    ("messages", "created_at"),
    ("model_providers", "created_at"),
    ("model_providers", "updated_at"),
    ("models", "created_at"),
    ("models", "updated_at"),
    ("permissions", "created_at"),
    ("refresh_tokens", "created_at"),
    ("retrieval_test_datasets", "created_at"),
    ("retrieval_test_datasets", "updated_at"),
    ("retrieval_test_runs", "started_at"),
    ("roles", "created_at"),
    ("roles", "updated_at"),
    ("users", "created_at"),
    ("users", "updated_at"),
)

_JSON_OBJECT_COLUMNS = (
    ("chunks", "metadata"),
    ("export_tasks", "options"),
    ("messages", "usage"),
    ("models", "parameters"),
)

_REQUIRED_REFERENCE_COLUMNS = (
    ("document_assets", "document_id"),
    ("document_chunks", "document_id"),
    ("document_tasks", "document_id"),
    ("documents", "knowledge_base_id"),
)

_TIMESTAMP_PAIRS = (
    ("conversations", "created_at", "updated_at"),
    ("documents", "created_at", "updated_at"),
    ("favorites", "saved_at", "updated_at"),
    ("knowledge_bases", "created_at", "updated_at"),
    ("model_providers", "created_at", "updated_at"),
    ("models", "created_at", "updated_at"),
    ("retrieval_test_datasets", "created_at", "updated_at"),
    ("roles", "created_at", "updated_at"),
    ("users", "created_at", "updated_at"),
)


def _update_nulls(table: str, column: str, sql_value: str) -> None:
    op.execute(
        sa.text(
            f'UPDATE "{table}" SET "{column}" = {sql_value} '
            f'WHERE "{column}" IS NULL'
        )
    )


def _assert_no_nulls(table: str, column: str) -> None:
    connection = op.get_bind()
    has_null = connection.execute(
        sa.text(
            f'SELECT EXISTS (SELECT 1 FROM "{table}" '
            f'WHERE "{column}" IS NULL)'
        )
    ).scalar_one()
    if has_null:
        raise RuntimeError(
            f"无法收紧 {table}.{column}：存在缺少父级引用的历史记录"
        )


def upgrade() -> None:
    for table, column in _REQUIRED_REFERENCE_COLUMNS:
        _assert_no_nulls(table, column)

    for table, created_column, updated_column in _TIMESTAMP_PAIRS:
        _update_nulls(
            table,
            created_column,
            f'COALESCE("{updated_column}", CURRENT_TIMESTAMP)',
        )
        _update_nulls(
            table,
            updated_column,
            f'COALESCE("{created_column}", CURRENT_TIMESTAMP)',
        )
    _update_nulls(
        "retrieval_test_runs",
        "started_at",
        'COALESCE("finished_at", CURRENT_TIMESTAMP)',
    )

    for table, column in _TIMESTAMP_COLUMNS:
        _update_nulls(table, column, "CURRENT_TIMESTAMP")
        op.alter_column(
            table,
            column,
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
        )

    for table, column in _JSON_OBJECT_COLUMNS:
        _update_nulls(table, column, "'{}'::jsonb")
        op.alter_column(
            table,
            column,
            existing_type=postgresql.JSONB(),
            nullable=False,
        )

    _update_nulls("messages", "citations", "'[]'::jsonb")
    op.alter_column(
        "messages",
        "citations",
        existing_type=postgresql.JSONB(),
        nullable=False,
    )

    _update_nulls("retrieval_test_datasets", "description", "''")
    op.alter_column(
        "retrieval_test_datasets",
        "description",
        existing_type=sa.Text(),
        nullable=False,
    )

    for table, column in _REQUIRED_REFERENCE_COLUMNS:
        op.alter_column(
            table,
            column,
            existing_type=sa.String(length=36),
            nullable=False,
        )


def downgrade() -> None:
    for table, column in reversed(_REQUIRED_REFERENCE_COLUMNS):
        op.alter_column(
            table,
            column,
            existing_type=sa.String(length=36),
            nullable=True,
        )

    op.alter_column(
        "retrieval_test_datasets",
        "description",
        existing_type=sa.Text(),
        nullable=True,
    )
    op.alter_column(
        "messages",
        "citations",
        existing_type=postgresql.JSONB(),
        nullable=True,
    )

    for table, column in reversed(_JSON_OBJECT_COLUMNS):
        op.alter_column(
            table,
            column,
            existing_type=postgresql.JSONB(),
            nullable=True,
        )

    for table, column in reversed(_TIMESTAMP_COLUMNS):
        op.alter_column(
            table,
            column,
            existing_type=sa.DateTime(timezone=True),
            nullable=True,
        )
