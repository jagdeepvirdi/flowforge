"""Add json to ck_report_format check constraint.

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-21
"""
from collections.abc import Sequence

from alembic import op

revision: str = '0004'
down_revision: str | None = '0003'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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
