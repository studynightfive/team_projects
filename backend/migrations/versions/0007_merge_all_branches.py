"""merge all employee branches

Revision ID: 0007_merge_all
Revises: 0002_documents, 0006_employee5_retrieval_tests
Create Date: 2026-07-18
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0007_merge_all"
down_revision: str | tuple[str, ...] | None = ("0002_documents", "0006_employee5_retrieval_tests")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass