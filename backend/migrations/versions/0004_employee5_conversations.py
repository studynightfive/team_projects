"""0004_employee5_conversations

Revision ID: 0004_employee5_conversations
Revises: 0003_employee5_chunks
Create Date: 2026-07-17

conversations + messages 表（员工5 提示词 04）
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_employee5_conversations"
down_revision: str | None = "0003_employee5_chunks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("kb_id", sa.dialects.postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("title", sa.String(200), nullable=False, server_default=""),
        sa.Column("is_pinned", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_archived", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("message_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_conv_user_updated", "conversations", ["user_id", "updated_at"])
    op.create_index("ix_conv_user_pinned", "conversations", ["user_id", "is_pinned"])
    op.create_index("ix_conv_deleted", "conversations", ["deleted_at"])

    op.create_table(
        "messages",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.dialects.postgresql.UUID(as_uuid=False),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text, nullable=False, server_default=""),
        sa.Column("citations", sa.dialects.postgresql.JSONB, server_default=sa.text("'[]'::jsonb")),
        sa.Column("answer_version", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("is_latest", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("parent_message_id", sa.dialects.postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("finish_reason", sa.String(32), nullable=True),
        sa.Column("usage", sa.dialects.postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_msg_conv_created", "messages", ["conversation_id", "created_at"])
    op.create_index("ix_msg_parent", "messages", ["parent_message_id"])
    op.create_index("ix_msg_conv_latest", "messages", ["conversation_id", "is_latest"])


def downgrade() -> None:
    op.drop_index("ix_msg_conv_latest", table_name="messages")
    op.drop_index("ix_msg_parent", table_name="messages")
    op.drop_index("ix_msg_conv_created", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_conv_deleted", table_name="conversations")
    op.drop_index("ix_conv_user_pinned", table_name="conversations")
    op.drop_index("ix_conv_user_updated", table_name="conversations")
    op.drop_table("conversations")
