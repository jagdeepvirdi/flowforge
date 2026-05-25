"""Add on_failure_webhook_url to ff_pipelines.

Revision ID: 0016
Revises: 0015
Create Date: 2026-05-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0016'
down_revision: Union[str, None] = '0015'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'ff_pipelines',
        sa.Column('on_failure_webhook_url', sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('ff_pipelines', 'on_failure_webhook_url')
