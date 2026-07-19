"""add favorites table

Revision ID: 0008_favorites
Revises: 0007_merge_all
Create Date: 2026-07-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_favorites"
down_revision: str | None = "0007_merge_all"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "favorites",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(24), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("summary", sa.Text, nullable=False, server_default=""),
        sa.Column(
            "tags",
            sa.dialects.postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("note", sa.Text, nullable=False, server_default=""),
        sa.Column("source_id", sa.String(128), nullable=True),
        sa.Column(
            "source_payload",
            sa.dialects.postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("saved_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_favorites_user_saved", "favorites", ["user_id", "saved_at"])
    op.create_index("ix_favorites_user_type", "favorites", ["user_id", "type"])


def downgrade() -> None:
    op.drop_index("ix_favorites_user_type", table_name="favorites")
    op.drop_index("ix_favorites_user_saved", table_name="favorites")
    op.drop_table("favorites")
