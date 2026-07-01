"""Add ff_project_members join table (team-scoped project access)

Revision ID: 0028_project_members
Revises: 0027_snowflake_bigquery_redshift
Create Date: 2026-07-01

"""
from collections.abc import Sequence

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql
from alembic import op

revision: str = '0028_project_members'
down_revision: str | None = '0027_snowflake_bigquery_redshift'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DEFAULT_PROJECT_ID = '00000000-0000-0000-0000-000000000001'


def upgrade() -> None:
    op.create_table(
        'ff_project_members',
        sa.Column('id',
                  sqlalchemy.dialects.postgresql.UUID(as_uuid=False),
                  primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id',
                  sqlalchemy.dialects.postgresql.UUID(as_uuid=False),
                  sa.ForeignKey('ff_projects.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('user_id',
                  sqlalchemy.dialects.postgresql.UUID(as_uuid=False),
                  sa.ForeignKey('ff_users.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('created_at',
                  sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()'),
                  nullable=False),
        sa.UniqueConstraint('project_id', 'user_id', name='uq_project_member'),
    )
    op.create_index('ix_project_member_project', 'ff_project_members', ['project_id'])
    op.create_index('ix_project_member_user',    'ff_project_members', ['user_id'])

    # Backfill: every existing user keeps access to the Default project, so
    # enforcing membership doesn't lock anyone out of resources they already had.
    op.execute(
        "INSERT INTO ff_project_members (id, project_id, user_id, created_at) "  # nosec B608
        f"SELECT gen_random_uuid(), '{_DEFAULT_PROJECT_ID}', id, NOW() "
        "FROM ff_users "
        f"WHERE EXISTS (SELECT 1 FROM ff_projects WHERE id = '{_DEFAULT_PROJECT_ID}') "
        "ON CONFLICT (project_id, user_id) DO NOTHING"
    )


def downgrade() -> None:
    op.drop_index('ix_project_member_user',    table_name='ff_project_members')
    op.drop_index('ix_project_member_project', table_name='ff_project_members')
    op.drop_table('ff_project_members')
