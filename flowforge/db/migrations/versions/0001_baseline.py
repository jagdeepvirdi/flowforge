"""Baseline schema — all FlowForge tables.

Revision ID: 0001
Revises:
Create Date: 2026-05-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Shorthand: UUID column stored as native PostgreSQL UUID, Python side as string.
_UUID = postgresql.UUID(as_uuid=False)


def upgrade() -> None:
    op.create_table(
        'ff_users',
        sa.Column('id', _UUID, primary_key=True),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime()),
        sa.UniqueConstraint('username', name='uq_users_username'),
    )

    op.create_table(
        'ff_recipient_groups',
        sa.Column('id', _UUID, primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('addresses', postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime()),
    )

    op.create_table(
        'ff_email_providers',
        sa.Column('id', _UUID, primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('provider_type', sa.String(20), nullable=False),
        sa.Column('config', sa.Text(), nullable=False),
        sa.Column('is_default', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime()),
        sa.CheckConstraint(
            "provider_type IN ('gmail', 'microsoft365', 'smtp')",
            name='ck_email_provider_type',
        ),
    )

    op.create_table(
        'ff_db_connections',
        sa.Column('id', _UUID, primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('db_type', sa.String(20), nullable=False),
        sa.Column('config', sa.Text(), nullable=False),
        sa.Column('is_default', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime()),
        sa.CheckConstraint(
            "db_type IN ('postgresql', 'oracle')",
            name='ck_db_connection_type',
        ),
    )

    op.create_table(
        'ff_report_configs',
        sa.Column('id', _UUID, primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('connection_id', _UUID,
                  sa.ForeignKey('ff_db_connections.id', ondelete='SET NULL')),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('format', sa.String(20), nullable=False),
        sa.Column('template_path', sa.String(500)),
        sa.Column('output_filename', sa.String(500), nullable=False),
        sa.Column('title', sa.String(255)),
        sa.Column('sheet_name', sa.String(100)),
        sa.Column('columns', postgresql.ARRAY(sa.Text())),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
        sa.CheckConstraint(
            "format IN ('excel', 'csv', 'pdf')",
            name='ck_report_format',
        ),
    )

    op.create_table(
        'ff_email_configs',
        sa.Column('id', _UUID, primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('provider_id', _UUID,
                  sa.ForeignKey('ff_email_providers.id', ondelete='SET NULL')),
        sa.Column('from_name', sa.String(255)),
        sa.Column('subject', sa.String(500), nullable=False),
        sa.Column('header_text', sa.String(500)),
        sa.Column('body_template', sa.Text(), nullable=False),
        sa.Column('recipient_group_id', _UUID,
                  sa.ForeignKey('ff_recipient_groups.id', ondelete='SET NULL')),
        sa.Column('to_addresses', postgresql.ARRAY(sa.Text())),
        sa.Column('cc_addresses', postgresql.ARRAY(sa.Text())),
        sa.Column('bcc_addresses', postgresql.ARRAY(sa.Text())),
        sa.Column('attachment_max_mb', sa.Integer(), server_default='10'),
        sa.Column('drive_folder_id', sa.String(255)),
        sa.Column('drive_share_message', sa.Text()),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )

    op.create_table(
        'ff_pipelines',
        sa.Column('id', _UUID, primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('schedule', sa.String(100)),
        sa.Column('enabled', sa.Boolean(), server_default='true'),
        sa.Column('timeout_minutes', sa.Integer(), server_default='60'),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
        sa.UniqueConstraint('name', name='uq_pipelines_name'),
    )

    op.create_table(
        'ff_pipeline_steps',
        sa.Column('id', _UUID, primary_key=True),
        sa.Column('pipeline_id', _UUID,
                  sa.ForeignKey('ff_pipelines.id', ondelete='CASCADE'), nullable=False),
        sa.Column('step_order', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('step_type', sa.String(50), nullable=False),
        sa.Column('config', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('on_error', sa.String(20), server_default='stop'),
        sa.Column('enabled', sa.Boolean(), server_default='true'),
        sa.CheckConstraint(
            "step_type IN ('db_procedure','db_query','report','email','drive_upload','ai_analyze')",
            name='ck_step_type',
        ),
        sa.CheckConstraint("on_error IN ('stop', 'continue')", name='ck_on_error'),
        sa.UniqueConstraint('pipeline_id', 'step_order', name='uq_pipeline_step_order'),
    )

    op.create_table(
        'ff_pipeline_variables',
        sa.Column('id', _UUID, primary_key=True),
        sa.Column('pipeline_id', _UUID,
                  sa.ForeignKey('ff_pipelines.id', ondelete='CASCADE'), nullable=False),
        sa.Column('var_key', sa.String(100), nullable=False),
        sa.Column('var_value', sa.Text(), nullable=False),
        sa.Column('is_secret', sa.Boolean(), server_default='false'),
        sa.UniqueConstraint('pipeline_id', 'var_key', name='uq_pipeline_var_key'),
    )

    op.create_table(
        'ff_pipeline_runs',
        sa.Column('id', _UUID, primary_key=True),
        sa.Column('pipeline_id', _UUID,
                  sa.ForeignKey('ff_pipelines.id', ondelete='SET NULL')),
        sa.Column('pipeline_name', sa.String(255), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime()),
        sa.Column('duration_ms', sa.Integer()),
        sa.Column('triggered_by', sa.String(50)),
        sa.Column('error_step', sa.String(255)),
        sa.Column('error_message', sa.Text()),
        sa.CheckConstraint(
            "status IN ('running','success','failed','cancelled')",
            name='ck_run_status',
        ),
    )

    op.create_table(
        'ff_step_runs',
        sa.Column('id', _UUID, primary_key=True),
        sa.Column('pipeline_run_id', _UUID,
                  sa.ForeignKey('ff_pipeline_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('step_name', sa.String(255), nullable=False),
        sa.Column('step_type', sa.String(50), nullable=False),
        sa.Column('step_order', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime()),
        sa.Column('duration_ms', sa.Integer()),
        sa.Column('rows_affected', sa.Integer()),
        sa.Column('output_path', sa.String(500)),
        sa.Column('drive_url', sa.String(500)),
        sa.Column('email_sent_to', postgresql.ARRAY(sa.Text())),
        sa.Column('logs', sa.Text()),
        sa.Column('error_message', sa.Text()),
        sa.CheckConstraint(
            "status IN ('running','success','failed','skipped')",
            name='ck_step_run_status',
        ),
    )


def downgrade() -> None:
    op.drop_table('ff_step_runs')
    op.drop_table('ff_pipeline_runs')
    op.drop_table('ff_pipeline_variables')
    op.drop_table('ff_pipeline_steps')
    op.drop_table('ff_pipelines')
    op.drop_table('ff_email_configs')
    op.drop_table('ff_report_configs')
    op.drop_table('ff_db_connections')
    op.drop_table('ff_email_providers')
    op.drop_table('ff_recipient_groups')
    op.drop_table('ff_users')
