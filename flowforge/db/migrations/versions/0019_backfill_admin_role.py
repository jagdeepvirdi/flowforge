"""Backfill role='admin' for the sole existing user created before 0018.

Migration 0018 added the role column with server_default='editor', which
downgraded any pre-existing seed admin to 'editor'. In the v1 single-user
setup, if there is exactly one user they must be the admin.

Revision ID: 0019
Revises: 0018
Create Date: 2026-05-26
"""
from typing import Sequence, Union

from alembic import op

revision: str = '0019'
down_revision: Union[str, None] = '0018'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE ff_users
        SET role = 'admin'
        WHERE role = 'editor'
          AND (SELECT COUNT(*) FROM ff_users) = 1
        """
    )


def downgrade() -> None:
    pass  # Not reversible — role history is not tracked
