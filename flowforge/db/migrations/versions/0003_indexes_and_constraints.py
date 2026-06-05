"""Add performance indexes and widen db_type check constraint.

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-20

DB-2: indexes on ff_pipeline_runs(pipeline_id, started_at DESC)
      and ff_step_runs(pipeline_run_id).
DB-3: expand ck_db_connection_type to include mysql, mssql, snowflake.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0003'
down_revision: str | None = '0002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # DB-2: performance indexes
    op.create_index(
        'ix_pipeline_runs_pipeline_started',
        'ff_pipeline_runs',
        ['pipeline_id', sa.text('started_at DESC')],
    )
    op.create_index(
        'ix_step_runs_pipeline_run',
        'ff_step_runs',
        ['pipeline_run_id'],
    )

    # DB-3: widen db_type constraint to include mysql, mssql, snowflake
    op.drop_constraint('ck_db_connection_type', 'ff_db_connections')
    op.create_check_constraint(
        'ck_db_connection_type',
        'ff_db_connections',
        "db_type IN ('postgresql', 'oracle', 'mysql', 'mssql', 'snowflake')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_db_connection_type', 'ff_db_connections')
    op.create_check_constraint(
        'ck_db_connection_type',
        'ff_db_connections',
        "db_type IN ('postgresql', 'oracle')",
    )

    op.drop_index('ix_step_runs_pipeline_run', 'ff_step_runs')
    op.drop_index('ix_pipeline_runs_pipeline_started', 'ff_pipeline_runs')
