"""Add ff_bulk_load_configs table and update step_type constraint.

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-22
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = '0005'
down_revision: str | None = '0004'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'ff_bulk_load_configs',
        sa.Column('id', UUID(as_uuid=False), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('connection_id', UUID(as_uuid=False), sa.ForeignKey('ff_db_connections.id', ondelete='SET NULL'), nullable=True),
        sa.Column('source_directory', sa.String(500), nullable=False),
        sa.Column('file_prefix', sa.String(255)),
        sa.Column('file_prefix_exclude', sa.String(255)),
        sa.Column('file_type', sa.String(20), server_default='csv'),
        sa.Column('delimiter', sa.String(5), server_default=','),
        sa.Column('header_rows', sa.Integer(), server_default='1'),
        sa.Column('footer_rows', sa.Integer(), server_default='0'),
        sa.Column('target_table', sa.String(255), nullable=False),
        sa.Column('load_mode', sa.String(20), server_default='append'),
        sa.Column('column_mapping', JSONB(), server_default='[]'),
        sa.Column('use_sqlloader', sa.Boolean(), server_default='false'),
        sa.Column('archive_directory', sa.String(500)),
        sa.Column('on_no_files', sa.String(20), server_default='skip'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )

    # Extend the step_type check constraint to include data_load and bulk_load
    op.drop_constraint('ck_step_type', 'ff_pipeline_steps', type_='check')
    op.create_check_constraint(
        'ck_step_type',
        'ff_pipeline_steps',
        "step_type IN ('db_procedure','db_query','report','email','drive_upload','ai_analyze','data_load','bulk_load')",
    )


def downgrade() -> None:
    op.drop_table('ff_bulk_load_configs')

    op.drop_constraint('ck_step_type', 'ff_pipeline_steps', type_='check')
    op.create_check_constraint(
        'ck_step_type',
        'ff_pipeline_steps',
        "step_type IN ('db_procedure','db_query','report','email','drive_upload','ai_analyze')",
    )
