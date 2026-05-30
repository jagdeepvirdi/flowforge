"""Add ssh_health_check to ck_step_type constraint

Revision ID: c4e8f2a1b9d3
Revises: 9c08f36f9ef8
Create Date: 2026-05-30 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = 'c4e8f2a1b9d3'
down_revision: Union[str, None] = '9c08f36f9ef8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_TYPES = (
    "'db_procedure','db_query','report','email','drive_upload',"
    "'data_load','bulk_load','onedrive_upload','ai_analyze','sftp_transfer',"
    "'ssh_command','db_health_check','data_report','ssh_health_check'"
)
_OLD_TYPES = (
    "'db_procedure','db_query','report','email','drive_upload',"
    "'data_load','bulk_load','onedrive_upload','ai_analyze','sftp_transfer',"
    "'ssh_command','db_health_check','data_report'"
)


def upgrade() -> None:
    op.drop_constraint('ck_step_type', 'ff_pipeline_steps')
    op.create_check_constraint(
        'ck_step_type',
        'ff_pipeline_steps',
        f'step_type IN ({_NEW_TYPES})',
    )


def downgrade() -> None:
    op.drop_constraint('ck_step_type', 'ff_pipeline_steps')
    op.create_check_constraint(
        'ck_step_type',
        'ff_pipeline_steps',
        f'step_type IN ({_OLD_TYPES})',
    )
