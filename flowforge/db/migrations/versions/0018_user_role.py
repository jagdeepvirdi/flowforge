"""Add role column to ff_users.

Revision ID: 0018
Revises: 0017
Create Date: 2026-05-25
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0018'
down_revision: str | None = '0017'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'ff_users',
        sa.Column('role', sa.String(20), nullable=False, server_default='editor'),
    )
    op.create_check_constraint(
        'ck_user_role',
        'ff_users',
        "role IN ('admin', 'editor', 'viewer')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_user_role', 'ff_users')
    op.drop_column('ff_users', 'role')
