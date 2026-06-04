"""Convert all timestamp columns to TIMESTAMPTZ.

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-20

Existing values are interpreted as UTC (USING col AT TIME ZONE 'UTC').
"""
from collections.abc import Sequence

from alembic import op

revision: str = '0002'
down_revision: str | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (table, column) pairs to convert
_TIMESTAMP_COLS = [
    ('ff_users',             'created_at'),
    ('ff_recipient_groups',  'created_at'),
    ('ff_email_providers',   'created_at'),
    ('ff_db_connections',    'created_at'),
    ('ff_report_configs',    'created_at'),
    ('ff_report_configs',    'updated_at'),
    ('ff_email_configs',     'created_at'),
    ('ff_email_configs',     'updated_at'),
    ('ff_pipelines',         'created_at'),
    ('ff_pipelines',         'updated_at'),
    ('ff_pipeline_runs',     'started_at'),
    ('ff_pipeline_runs',     'finished_at'),
    ('ff_step_runs',         'started_at'),
    ('ff_step_runs',         'finished_at'),
]


def upgrade() -> None:
    for table, col in _TIMESTAMP_COLS:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {col} "
            f"TYPE TIMESTAMPTZ USING {col} AT TIME ZONE 'UTC'"
        )


def downgrade() -> None:
    for table, col in _TIMESTAMP_COLS:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {col} "
            f"TYPE TIMESTAMP WITHOUT TIME ZONE USING {col} AT TIME ZONE 'UTC'"
        )
