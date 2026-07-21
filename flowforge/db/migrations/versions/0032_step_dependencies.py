"""Add step-level dependency table for arbitrary DAG edges within a pipeline

Revision ID: 0032_step_dependencies
Revises: 0031_email_body_format
Create Date: 2026-07-22

"""
from collections.abc import Sequence

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql
from alembic import op

revision: str = '0032_step_dependencies'
down_revision: str | None = '0031_email_body_format'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Step-level dependencies — arbitrary step-to-step edges within a single pipeline
    # (Phase 14 Option B, Milestone 1). Additive only: ff_pipeline_steps is untouched, and the
    # runner keeps using step_order/parallel_group until a pipeline actually has edges here.
    op.create_table(
        'ff_step_dependencies',
        sa.Column('id',
                  sqlalchemy.dialects.postgresql.UUID(as_uuid=False),
                  primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('pipeline_id',
                  sqlalchemy.dialects.postgresql.UUID(as_uuid=False),
                  sa.ForeignKey('ff_pipelines.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('upstream_step_id',
                  sqlalchemy.dialects.postgresql.UUID(as_uuid=False),
                  sa.ForeignKey('ff_pipeline_steps.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('downstream_step_id',
                  sqlalchemy.dialects.postgresql.UUID(as_uuid=False),
                  sa.ForeignKey('ff_pipeline_steps.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('created_at',
                  sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()'),
                  nullable=False),
        sa.UniqueConstraint('upstream_step_id', 'downstream_step_id', name='uq_step_dependency'),
        sa.CheckConstraint('upstream_step_id != downstream_step_id', name='ck_no_self_step_dependency'),
    )
    op.create_index('ix_step_dep_pipeline',   'ff_step_dependencies', ['pipeline_id'])
    op.create_index('ix_step_dep_upstream',   'ff_step_dependencies', ['upstream_step_id'])
    op.create_index('ix_step_dep_downstream', 'ff_step_dependencies', ['downstream_step_id'])


def downgrade() -> None:
    op.drop_index('ix_step_dep_downstream', table_name='ff_step_dependencies')
    op.drop_index('ix_step_dep_upstream',   table_name='ff_step_dependencies')
    op.drop_index('ix_step_dep_pipeline',   table_name='ff_step_dependencies')
    op.drop_table('ff_step_dependencies')
