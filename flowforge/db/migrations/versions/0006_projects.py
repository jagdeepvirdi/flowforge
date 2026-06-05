"""Add ff_projects table and project_id FK to pipelines, reports, emails, recipients.

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-23
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = '0006'
down_revision: str | None = '0005'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Fixed UUID so the Default project is always identifiable across environments.
DEFAULT_PROJECT_ID = '00000000-0000-0000-0000-000000000001'

_SCOPED_TABLES = (
    'ff_pipelines',
    'ff_report_configs',
    'ff_email_configs',
    'ff_recipient_groups',
)


def upgrade() -> None:
    # 1. Create ff_projects table
    op.create_table(
        'ff_projects',
        sa.Column('id', UUID(as_uuid=False), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('color', sa.String(20), server_default='#6366f1'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )

    # 2. Seed the Default project with a fixed, predictable UUID
    op.execute(
        f"INSERT INTO ff_projects (id, name, is_default, created_at) "  # nosec B608
        f"VALUES ('{DEFAULT_PROJECT_ID}', 'Default', true, NOW())"
    )

    # 3. Add nullable project_id columns to all scoped tables
    for table in _SCOPED_TABLES:
        op.add_column(
            table,
            sa.Column(
                'project_id',
                UUID(as_uuid=False),
                sa.ForeignKey('ff_projects.id', ondelete='SET NULL'),
                nullable=True,
            ),
        )

    # 4. Backfill all existing rows to the Default project
    for table in _SCOPED_TABLES:
        op.execute(
            f"UPDATE {table} SET project_id = '{DEFAULT_PROJECT_ID}' WHERE project_id IS NULL"  # nosec B608
        )


def downgrade() -> None:
    for table in _SCOPED_TABLES:
        op.drop_column(table, 'project_id')

    op.drop_table('ff_projects')
