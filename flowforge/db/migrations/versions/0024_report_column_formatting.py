"""Add column_formatting JSONB to report configs

Revision ID: 0024_report_column_formatting
Revises: 0023_pipeline_deps_parallel
Create Date: 2026-05-30

"""
from collections.abc import Sequence

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql
from alembic import op

revision: str = '0024_report_column_formatting'
down_revision: str | None = '0023_pipeline_deps_parallel'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'ff_report_configs',
        sa.Column(
            'column_formatting',
            sqlalchemy.dialects.postgresql.JSONB(),
            nullable=True,
            comment='Per-column formatting rules for Excel: number_format, width, conditional fill/font',
        ),
    )


def downgrade() -> None:
    op.drop_column('ff_report_configs', 'column_formatting')
