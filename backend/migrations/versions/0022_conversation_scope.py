"""为搜索会话保存多知识库范围。

Revision ID: 0022_conversation_scope
Revises: 0021_unique_document_names
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0022_conversation_scope"
down_revision: str | None = "0021_unique_document_names"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column(
            "knowledge_base_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    # 旧会话只有 kb_id；迁移后保持原有知识库范围不变。
    op.execute(
        """
        UPDATE conversations
        SET knowledge_base_ids = jsonb_build_array(kb_id)
        WHERE knowledge_base_ids = '[]'::jsonb
        """
    )
    op.alter_column("conversations", "knowledge_base_ids", server_default=None)


def downgrade() -> None:
    op.drop_column("conversations", "knowledge_base_ids")
