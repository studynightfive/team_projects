"""add user session version

Revision ID: 0013_user_session_version
Revises: 0012_schema_consistency
Create Date: 2026-07-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0013_user_session_version"
down_revision = "0012_schema_consistency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "session_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.alter_column("users", "session_version", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "session_version")
