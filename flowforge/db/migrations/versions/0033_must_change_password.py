"""Add must_change_password flag to ff_users

Revision ID: 0033_must_change_password
Revises: 0032_step_dependencies
Create Date: 2026-07-25

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0033_must_change_password'
down_revision: str | None = '0032_step_dependencies'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Forces a set-new-password step before a full session is issued — set on
    # admin-invited users (see users.py create_user) until they set their own password.
    op.add_column('ff_users', sa.Column('must_change_password', sa.Boolean, nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('ff_users', 'must_change_password')
