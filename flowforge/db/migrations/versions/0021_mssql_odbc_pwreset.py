"""Add MSSQL/ODBC connection types, user email, and password reset tokens

Revision ID: 0021_mssql_odbc_pwreset
Revises: 0020_mfa_sso
Create Date: 2026-05-30

"""
from collections.abc import Sequence

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql
from alembic import op

revision: str = '0021_mssql_odbc_pwreset'
down_revision: str | None = '0020_mfa_sso'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Expand db_type constraint to include mssql and odbc
    op.drop_constraint('ck_db_connection_type', 'ff_db_connections')
    op.create_check_constraint(
        'ck_db_connection_type',
        'ff_db_connections',
        "db_type IN ('postgresql', 'oracle', 'mysql', 'mssql', 'odbc')",
    )

    # User email address (optional — used for password reset)
    op.add_column('ff_users', sa.Column('email', sa.String(255), nullable=True))
    op.create_index('ix_ff_users_email', 'ff_users', ['email'], unique=False)

    # Password reset tokens (single-use, 1h TTL)
    op.create_table(
        'ff_password_reset_tokens',
        sa.Column('token',      sa.String(64),                               primary_key=True),
        sa.Column('user_id',    sa.dialects.postgresql.UUID(as_uuid=False),  sa.ForeignKey('ff_users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),                  server_default=sa.text('NOW()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True),                  nullable=False),
        sa.Column('used_at',    sa.DateTime(timezone=True),                  nullable=True),
    )
    op.create_index('ix_ff_pwreset_user_id', 'ff_password_reset_tokens', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_ff_pwreset_user_id',  table_name='ff_password_reset_tokens')
    op.drop_table('ff_password_reset_tokens')
    op.drop_index('ix_ff_users_email',       table_name='ff_users')
    op.drop_column('ff_users', 'email')
    op.drop_constraint('ck_db_connection_type', 'ff_db_connections')
    op.create_check_constraint(
        'ck_db_connection_type',
        'ff_db_connections',
        "db_type IN ('postgresql', 'oracle', 'mysql')",
    )
