"""为会话知识库和消息父节点补齐引用完整性约束。

Revision ID: 0014_conversation_integrity
Revises: 0013_user_session_version
Create Date: 2026-07-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_conversation_integrity"
down_revision: str | None = "0013_user_session_version"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "conversations",
        "kb_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=False),
        type_=sa.String(36),
        existing_nullable=False,
        postgresql_using="kb_id::text",
    )
    op.create_foreign_key(
        "fk_conversations_kb_id_knowledge_bases",
        "conversations",
        "knowledge_bases",
        ["kb_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_messages_parent_message_id_messages",
        "messages",
        "messages",
        ["parent_message_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_messages_parent_message_id_messages",
        "messages",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_conversations_kb_id_knowledge_bases",
        "conversations",
        type_="foreignkey",
    )
    op.alter_column(
        "conversations",
        "kb_id",
        existing_type=sa.String(36),
        type_=sa.dialects.postgresql.UUID(as_uuid=False),
        existing_nullable=False,
        postgresql_using="kb_id::uuid",
    )
