"""新增部门归属并把知识库唯一性收敛到部门内。

Revision ID: 0016_departments
Revises: 0015_embedding_vector_1536
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_departments"
down_revision: str | None = "0015_embedding_vector_1536"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_DEPARTMENT_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "admin_user_id",
            sa.String(36),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_departments_admin_user_id_users",
        "departments",
        "users",
        ["admin_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "uq_departments_name_normalized",
        "departments",
        [sa.text("lower(btrim(name))")],
        unique=True,
    )
    op.create_index(
        "ix_departments_admin_user_id", "departments", ["admin_user_id"]
    )
    op.execute(
        sa.text(
            "INSERT INTO departments (id, name, description) "
            "VALUES (:id, '默认部门', '承接升级前已有用户与知识库')"
        ).bindparams(id=DEFAULT_DEPARTMENT_ID)
    )

    op.add_column(
        "users",
        sa.Column(
            "department_id",
            sa.String(36),
            sa.ForeignKey("departments.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_users_department_id", "users", ["department_id"])
    op.execute(
        sa.text("UPDATE users SET department_id = :id WHERE department_id IS NULL").bindparams(
            id=DEFAULT_DEPARTMENT_ID
        )
    )
    op.execute(
        sa.text(
            "UPDATE departments SET admin_user_id = ("
            "SELECT ur.user_id FROM user_roles AS ur "
            "JOIN roles AS r ON r.id = ur.role_id "
            "WHERE r.name = '超级管理员' ORDER BY ur.user_id LIMIT 1"
            ") WHERE id = :id AND admin_user_id IS NULL"
        ).bindparams(id=DEFAULT_DEPARTMENT_ID)
    )

    op.add_column(
        "knowledge_bases",
        sa.Column(
            "department_id",
            sa.String(36),
            sa.ForeignKey("departments.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.execute(
        sa.text(
            "UPDATE knowledge_bases SET department_id = :id "
            "WHERE department_id IS NULL"
        ).bindparams(id=DEFAULT_DEPARTMENT_ID)
    )
    op.alter_column("knowledge_bases", "department_id", nullable=False)
    op.create_index(
        "ix_knowledge_bases_department_id", "knowledge_bases", ["department_id"]
    )
    op.drop_index(
        "uq_knowledge_bases_name_normalized", table_name="knowledge_bases"
    )
    op.create_index(
        "uq_knowledge_bases_department_name_normalized",
        "knowledge_bases",
        ["department_id", sa.text("lower(btrim(name))")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_knowledge_bases_department_name_normalized",
        table_name="knowledge_bases",
    )
    op.execute(
        """
        WITH ranked AS (
            SELECT id, btrim(name) AS base_name,
                row_number() OVER (
                    PARTITION BY lower(btrim(name))
                    ORDER BY created_at NULLS LAST, id
                ) AS duplicate_no
            FROM knowledge_bases
        )
        UPDATE knowledge_bases AS kb
        SET name = left(ranked.base_name, 170)
            || ' (department-' || left(kb.department_id, 8) || ')'
        FROM ranked
        WHERE kb.id = ranked.id AND ranked.duplicate_no > 1
        """
    )
    op.create_index(
        "uq_knowledge_bases_name_normalized",
        "knowledge_bases",
        [sa.text("lower(btrim(name))")],
        unique=True,
    )
    op.drop_index("ix_knowledge_bases_department_id", table_name="knowledge_bases")
    op.drop_column("knowledge_bases", "department_id")
    op.drop_index("ix_users_department_id", table_name="users")
    op.drop_column("users", "department_id")
    op.drop_index("ix_departments_admin_user_id", table_name="departments")
    op.drop_index("uq_departments_name_normalized", table_name="departments")
    op.drop_table("departments")
