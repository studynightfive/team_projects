"""prevent duplicate knowledge base names

Revision ID: 0009_unique_kb_names
Revises: 0008_favorites
Create Date: 2026-07-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009_unique_kb_names"
down_revision = "0008_favorites"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE knowledge_bases
        SET name = 'unnamed-kb-' || left(id, 8)
        WHERE btrim(name) = ''
        """
    )
    op.execute(
        """
        UPDATE knowledge_bases
        SET name = btrim(name)
        WHERE name <> btrim(name)
        """
    )
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                btrim(name) AS base_name,
                row_number() OVER (
                    PARTITION BY lower(btrim(name))
                    ORDER BY created_at NULLS LAST, id
                ) AS duplicate_no
            FROM knowledge_bases
        )
        UPDATE knowledge_bases AS kb
        SET name = left(ranked.base_name, 180)
            || ' (duplicate-'
            || ranked.duplicate_no
            || '-'
            || left(ranked.id, 8)
            || ')'
        FROM ranked
        WHERE kb.id = ranked.id
          AND ranked.duplicate_no > 1
        """
    )
    op.create_index(
        "uq_knowledge_bases_name_normalized",
        "knowledge_bases",
        [sa.text("lower(btrim(name))")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_knowledge_bases_name_normalized", table_name="knowledge_bases")
