"""Add pipeline dependencies table and parallel_group to pipeline steps

Revision ID: 0023_pipeline_deps_parallel
Revises: 0021_mssql_odbc_pwreset
Create Date: 2026-05-30

"""
from collections.abc import Sequence

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql
from alembic import op

revision: str = '0023_pipeline_deps_parallel'
down_revision: str | None = '0021_mssql_odbc_pwreset'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Parallel step execution — steps with the same group name run concurrently
    op.add_column(
        'ff_pipeline_steps',
        sa.Column('parallel_group', sa.String(100), nullable=True),
    )

    # Pipeline dependencies — downstream runs automatically after all upstreams succeed
    op.create_table(
        'ff_pipeline_dependencies',
        sa.Column('id',
                  sqlalchemy.dialects.postgresql.UUID(as_uuid=False),
                  primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('upstream_id',
                  sqlalchemy.dialects.postgresql.UUID(as_uuid=False),
                  sa.ForeignKey('ff_pipelines.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('downstream_id',
                  sqlalchemy.dialects.postgresql.UUID(as_uuid=False),
                  sa.ForeignKey('ff_pipelines.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('created_at',
                  sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()'),
                  nullable=False),
        sa.UniqueConstraint('upstream_id', 'downstream_id', name='uq_pipeline_dependency'),
        sa.CheckConstraint('upstream_id != downstream_id', name='ck_no_self_dependency'),
    )
    op.create_index('ix_pipeline_dep_upstream',   'ff_pipeline_dependencies', ['upstream_id'])
    op.create_index('ix_pipeline_dep_downstream', 'ff_pipeline_dependencies', ['downstream_id'])


def downgrade() -> None:
    op.drop_index('ix_pipeline_dep_downstream', table_name='ff_pipeline_dependencies')
    op.drop_index('ix_pipeline_dep_upstream',   table_name='ff_pipeline_dependencies')
    op.drop_table('ff_pipeline_dependencies')
    op.drop_column('ff_pipeline_steps', 'parallel_group')
