"""Add json to ck_report_format check constraint.

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-21
"""
from typing import Sequence, Union

from alembic import op

revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('ck_report_format', 'ff_report_configs')
    op.create_check_constraint(
        'ck_report_format',
        'ff_report_configs',
        "format IN ('excel', 'csv', 'pdf', 'json')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_report_format', 'ff_report_configs')
    op.create_check_constraint(
        'ck_report_format',
        'ff_report_configs',
        "format IN ('excel', 'csv', 'pdf')",
    )
