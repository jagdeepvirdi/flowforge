"""Add ff_system_settings singleton table (DB-backed retention overrides)

Revision ID: 0029_system_settings
Revises: 0028_project_members
Create Date: 2026-07-09

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0029_system_settings'
down_revision: str | None = '0028_project_members'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'ff_system_settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('run_retention_days',   sa.Integer(), nullable=True),
        sa.Column('audit_retention_days', sa.Integer(), nullable=True),
        sa.Column('output_ttl_days',      sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_by', sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('ff_system_settings')
