"""清理知识库编辑者账号的冗余普通用户角色。

Revision ID: 0017_single_builtin_user_role
Revises: 0016_departments
Create Date: 2026-07-21
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0017_single_builtin_user_role"
down_revision: str | None = "0016_departments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM user_roles AS normal_assignment
        USING roles AS normal_role
        WHERE normal_assignment.role_id = normal_role.id
          AND normal_role.name = '普通用户'
          AND EXISTS (
              SELECT 1
              FROM user_roles AS editor_assignment
              JOIN roles AS editor_role ON editor_role.id = editor_assignment.role_id
              WHERE editor_assignment.user_id = normal_assignment.user_id
                AND editor_role.name = '知识库编辑者'
          )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        INSERT INTO user_roles (user_id, role_id)
        SELECT editor_assignment.user_id, normal_role.id
        FROM user_roles AS editor_assignment
        JOIN roles AS editor_role ON editor_role.id = editor_assignment.role_id
        CROSS JOIN roles AS normal_role
        WHERE editor_role.name = '知识库编辑者'
          AND normal_role.name = '普通用户'
        ON CONFLICT DO NOTHING
        """
    )
