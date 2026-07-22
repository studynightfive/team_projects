"""Add personal knowledge bases and per-document chunk strategy.

Revision ID: 0018_personal_kb_chunk_strategy
Revises: 0017_single_builtin_user_role
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_personal_kb_chunk_strategy"
down_revision: str | None = "0017_single_builtin_user_role"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _stable_uuid(prefix: str, value_sql: str) -> str:
    digest = f"md5('{prefix}' || {value_sql})"
    return (
        f"substr({digest}, 1, 8) || '-' || substr({digest}, 9, 4) || '-' || "
        f"substr({digest}, 13, 4) || '-' || substr({digest}, 17, 4) || '-' || "
        f"substr({digest}, 21, 12)"
    )


def upgrade() -> None:
    op.add_column(
        "knowledge_bases",
        sa.Column("kind", sa.String(16), nullable=False, server_default="enterprise"),
    )
    op.add_column(
        "knowledge_bases",
        sa.Column(
            "owner_user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_knowledge_bases_kind_owner",
        "knowledge_bases",
        "(kind = 'enterprise' AND owner_user_id IS NULL) OR "
        "(kind = 'personal' AND owner_user_id IS NOT NULL)",
    )
    op.drop_index(
        "uq_knowledge_bases_department_name_normalized",
        table_name="knowledge_bases",
    )
    op.create_index(
        "uq_knowledge_bases_enterprise_department_name",
        "knowledge_bases",
        ["department_id", sa.text("lower(btrim(name))")],
        unique=True,
        postgresql_where=sa.text("kind = 'enterprise'"),
    )
    op.create_index(
        "uq_knowledge_bases_personal_owner",
        "knowledge_bases",
        ["owner_user_id"],
        unique=True,
        postgresql_where=sa.text("kind = 'personal'"),
    )

    personal_kb_id = _stable_uuid("personal-kb:", "u.id")
    op.execute(
        sa.text(
            f"""
            INSERT INTO knowledge_bases (
                id, name, description, department_id, kind, owner_user_id,
                status, chunk_size, chunk_overlap
            )
            SELECT
                {personal_kb_id},
                u.display_name || '的个人知识库',
                '用于存放个人文档，仅本人可访问',
                COALESCE(u.department_id, :default_department_id),
                'personal',
                u.id,
                'active',
                800,
                120
            FROM users u
            WHERE NOT EXISTS (
                SELECT 1 FROM knowledge_bases kb
                WHERE kb.kind = 'personal' AND kb.owner_user_id = u.id
            )
            """
        ).bindparams(default_department_id="00000000-0000-0000-0000-000000000001")
    )
    permission_id = _stable_uuid("personal-kb-permission:", "u.id")
    op.execute(
        sa.text(
            f"""
            INSERT INTO knowledge_base_permissions (
                id, subject_type, subject_id, kb_id, access_level
            )
            SELECT
                {permission_id}, 'user', u.id, kb.id, 'admin'
            FROM users u
            JOIN knowledge_bases kb
              ON kb.kind = 'personal' AND kb.owner_user_id = u.id
            WHERE NOT EXISTS (
                SELECT 1 FROM knowledge_base_permissions p
                WHERE p.kb_id = kb.id
                  AND p.subject_type = 'user'
                  AND p.subject_id = u.id
            )
            """
        )
    )

    op.add_column(
        "documents",
        sa.Column("chunk_strategy", sa.String(16), nullable=False, server_default="format"),
    )
    op.add_column(
        "documents",
        sa.Column("chunk_size", sa.Integer(), nullable=False, server_default="800"),
    )
    op.add_column(
        "documents",
        sa.Column("chunk_overlap", sa.Integer(), nullable=False, server_default="120"),
    )
    op.create_check_constraint(
        "ck_documents_chunk_strategy",
        "documents",
        "chunk_strategy IN ('fixed', 'semantic', 'recursive', 'format')",
    )
    op.create_check_constraint(
        "ck_documents_chunk_parameters",
        "documents",
        "chunk_size BETWEEN 100 AND 4000 AND chunk_overlap >= 0 "
        "AND chunk_overlap < chunk_size",
    )


def downgrade() -> None:
    op.drop_constraint("ck_documents_chunk_parameters", "documents", type_="check")
    op.drop_constraint("ck_documents_chunk_strategy", "documents", type_="check")
    op.drop_column("documents", "chunk_overlap")
    op.drop_column("documents", "chunk_size")
    op.drop_column("documents", "chunk_strategy")

    op.execute(sa.text("DELETE FROM knowledge_bases WHERE kind = 'personal'"))
    op.drop_index("uq_knowledge_bases_personal_owner", table_name="knowledge_bases")
    op.drop_index(
        "uq_knowledge_bases_enterprise_department_name",
        table_name="knowledge_bases",
    )
    op.create_index(
        "uq_knowledge_bases_department_name_normalized",
        "knowledge_bases",
        ["department_id", sa.text("lower(btrim(name))")],
        unique=True,
    )
    op.drop_constraint("ck_knowledge_bases_kind_owner", "knowledge_bases", type_="check")
    op.drop_column("knowledge_bases", "owner_user_id")
    op.drop_column("knowledge_bases", "kind")
