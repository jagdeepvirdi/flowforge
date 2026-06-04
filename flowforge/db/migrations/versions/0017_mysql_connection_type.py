"""Add 'mysql' to ff_db_connections db_type check constraint.

Revision ID: 0017
Revises: 0016
Create Date: 2026-05-25
"""
from collections.abc import Sequence

from alembic import op

revision: str = '0017'
down_revision: str | None = '0016'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint('ck_db_connection_type', 'ff_db_connections')
    op.create_check_constraint(
        'ck_db_connection_type',
        'ff_db_connections',
        "db_type IN ('postgresql', 'oracle', 'mysql')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_db_connection_type', 'ff_db_connections')
    op.create_check_constraint(
        'ck_db_connection_type',
        'ff_db_connections',
        "db_type IN ('postgresql', 'oracle')",
    )
