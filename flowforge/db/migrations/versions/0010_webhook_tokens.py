"""Add ff_webhook_tokens for API/external trigger support.

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-23
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

_UUID = postgresql.UUID(as_uuid=False)

revision: str = '0010'
down_revision: str | None = '0009'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'ff_webhook_tokens',
        sa.Column('id',           _UUID,                      primary_key=True),
        sa.Column('pipeline_id',  _UUID,                      sa.ForeignKey('ff_pipelines.id', ondelete='CASCADE'), nullable=False),
        sa.Column('label',        sa.String(100),             nullable=False, server_default=''),
        sa.Column('token_hash',   sa.String(64),              nullable=False, unique=True),
        sa.Column('enabled',      sa.Boolean,                 nullable=False, server_default='true'),
        sa.Column('last_used_at', sa.DateTime(timezone=True)),
        sa.Column('created_at',   sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_ff_webhook_tokens_pipeline_id', 'ff_webhook_tokens', ['pipeline_id'])


def downgrade() -> None:
    op.drop_index('ix_ff_webhook_tokens_pipeline_id', table_name='ff_webhook_tokens')
    op.drop_table('ff_webhook_tokens')
