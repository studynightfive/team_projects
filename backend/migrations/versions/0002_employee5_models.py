"""0002_employee5_models

Revision ID: 0002_employee5_models
Revises: 0001_init_core_tables
Create Date: 2026-07-17

模型管理表（员工5 提示词 01 §4.5）
'''
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_employee5_models"
down_revision: str | None = "0001_init_core_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "model_providers",
        sa.Column("code", sa.String(32), primary_key=True),
        sa.Column("display_name", sa.String(64), nullable=False),
        sa.Column("base_url", sa.String(512), nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "models",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("provider_code", sa.String(32), sa.ForeignKey("model_providers.code", ondelete="RESTRICT"), nullable=False),
        sa.Column("model_name", sa.String(128), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("parameters", sa.dialects.postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("api_key_encrypted", sa.Text, nullable=True),
        sa.Column("dimensions", sa.Integer, nullable=True),
        sa.Column("distance", sa.String(16), nullable=True),
        sa.Column("top_n", sa.Integer, nullable=True),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_models_provider_kind", "models", ["provider_code", "kind"])


def downgrade() -> None:
    op.drop_index("ix_models_provider_kind", table_name="models")
    op.drop_table("models")
    op.drop_table("model_providers")