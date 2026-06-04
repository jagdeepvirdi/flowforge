"""Add ff_token_blocklist for JWT revocation.

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-23
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0008'
down_revision: str | None = '0007'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'ff_token_blocklist',
        sa.Column('jti',        sa.String(36),                    primary_key=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True),       nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True),       nullable=False),
    )
    op.create_index('ix_token_blocklist_expires_at', 'ff_token_blocklist', ['expires_at'])


def downgrade() -> None:
    op.drop_index('ix_token_blocklist_expires_at', table_name='ff_token_blocklist')
    op.drop_table('ff_token_blocklist')
