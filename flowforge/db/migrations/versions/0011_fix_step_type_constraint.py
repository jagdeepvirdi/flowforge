"""Fix ff_pipeline_steps step_type check constraint.

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-24

BUG-4: constraint only covered the original 6 types; data_load and bulk_load
were accepted by the API but rejected at the DB level, causing unhandled 500s.
ai_analyze was in the constraint but has no implementation; removed until the
AI features track ships.
"""
from collections.abc import Sequence

from alembic import op

revision: str = '0011'
down_revision: str | None = '0010'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint('ck_step_type', 'ff_pipeline_steps')
    op.create_check_constraint(
        'ck_step_type',
        'ff_pipeline_steps',
        "step_type IN ('db_procedure','db_query','report','email','drive_upload','data_load','bulk_load')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_step_type', 'ff_pipeline_steps')
    op.create_check_constraint(
        'ck_step_type',
        'ff_pipeline_steps',
        "step_type IN ('db_procedure','db_query','report','email','drive_upload','ai_analyze')",
    )
