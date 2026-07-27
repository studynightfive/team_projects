"""为检索指标增加主商品实体快照。

Revision ID: 0023_metric_product_entity
Revises: 0022_conversation_scope
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023_metric_product_entity"
down_revision: str | None = "0022_conversation_scope"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "retrieval_metrics",
        sa.Column("primary_product_id", sa.String(36), nullable=True),
    )
    op.add_column(
        "retrieval_metrics",
        sa.Column("primary_product_name", sa.String(500), nullable=True),
    )
    op.create_index(
        "ix_retrieval_metrics_product_created",
        "retrieval_metrics",
        ["department_id", "primary_product_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_retrieval_metrics_product_created",
        table_name="retrieval_metrics",
    )
    op.drop_column("retrieval_metrics", "primary_product_name")
    op.drop_column("retrieval_metrics", "primary_product_id")
