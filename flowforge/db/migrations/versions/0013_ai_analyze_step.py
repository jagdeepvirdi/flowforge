"""Add ai_analyze to ff_pipeline_steps step_type check constraint.

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-25
"""
from typing import Sequence, Union

from alembic import op

revision: str = '0013'
down_revision: Union[str, None] = '0012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_TYPES = (
    "'db_procedure','db_query','report','email',"
    "'drive_upload','data_load','bulk_load','onedrive_upload','ai_analyze'"
)
_OLD_TYPES = (
    "'db_procedure','db_query','report','email',"
    "'drive_upload','data_load','bulk_load','onedrive_upload'"
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
