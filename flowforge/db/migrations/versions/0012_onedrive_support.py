"""Add onedrive_upload step type and onedrive_folder_id to email configs.

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0012'
down_revision: Union[str, None] = '0011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_TYPES = (
    "'db_procedure','db_query','report','email',"
    "'drive_upload','data_load','bulk_load','onedrive_upload'"
)
_OLD_TYPES = (
    "'db_procedure','db_query','report','email',"
    "'drive_upload','data_load','bulk_load'"
)


def upgrade() -> None:
    op.drop_constraint('ck_step_type', 'ff_pipeline_steps')
    op.create_check_constraint(
        'ck_step_type',
        'ff_pipeline_steps',
        f'step_type IN ({_NEW_TYPES})',
    )
    op.add_column(
        'ff_email_configs',
        sa.Column('onedrive_folder_id', sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('ff_email_configs', 'onedrive_folder_id')
    op.drop_constraint('ck_step_type', 'ff_pipeline_steps')
    op.create_check_constraint(
        'ck_step_type',
        'ff_pipeline_steps',
        f'step_type IN ({_OLD_TYPES})',
    )
