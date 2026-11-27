"""Add ff_token_map: optional encrypted reverse lookup for subscriber-identifier tokens

Revision ID: 0034_token_map
Revises: 0033_must_change_password
Create Date: 2026-11-27

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0034_token_map'
down_revision: str | None = '0033_must_change_password'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'ff_token_map',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('token', sa.String(64), nullable=False),
        sa.Column('kind', sa.String(20), nullable=False),
        sa.Column('ciphertext', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('token'),     # unnamed, like the model's unique=True (ff_token_map_token_key)
    )
    op.create_index('ix_ff_token_map_last_seen_at', 'ff_token_map', ['last_seen_at'])


def downgrade() -> None:
    op.drop_index('ix_ff_token_map_last_seen_at', table_name='ff_token_map')
    op.drop_table('ff_token_map')
