"""Add index on ff_pipeline_variables(pipeline_id).

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-23
"""
from collections.abc import Sequence

from alembic import op

revision: str = '0007'
down_revision: str | None = '0006'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        'ix_pipeline_variables_pipeline_id',
        'ff_pipeline_variables',
        ['pipeline_id'],
    )


def downgrade() -> None:
    op.drop_index(
        'ix_pipeline_variables_pipeline_id',
        table_name='ff_pipeline_variables',
    )
