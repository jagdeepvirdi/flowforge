"""Add MFA and SSO columns to ff_users

Revision ID: 0020_mfa_sso
Revises: c4e8f2a1b9d3
Create Date: 2026-05-30

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0020_mfa_sso'
down_revision: Union[str, None] = 'c4e8f2a1b9d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # MFA (TOTP) — secret and backup codes stored AES-256 encrypted
    op.add_column('ff_users', sa.Column('mfa_secret',       sa.Text,         nullable=True))
    op.add_column('ff_users', sa.Column('mfa_enabled',      sa.Boolean,      nullable=False, server_default='false'))
    op.add_column('ff_users', sa.Column('mfa_backup_codes', sa.Text,         nullable=True))

    # SSO — provider and normalised email for account matching
    op.add_column('ff_users', sa.Column('sso_provider', sa.String(20),  nullable=True))
    op.add_column('ff_users', sa.Column('sso_email',    sa.String(255), nullable=True))

    op.create_index('ix_ff_users_sso_email', 'ff_users', ['sso_email'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_ff_users_sso_email', table_name='ff_users')
    op.drop_column('ff_users', 'sso_email')
    op.drop_column('ff_users', 'sso_provider')
    op.drop_column('ff_users', 'mfa_backup_codes')
    op.drop_column('ff_users', 'mfa_enabled')
    op.drop_column('ff_users', 'mfa_secret')
