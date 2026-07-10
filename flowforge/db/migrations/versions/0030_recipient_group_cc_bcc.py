"""Add cc_addresses/bcc_addresses to ff_recipient_groups

Recipient groups previously only carried a flat "addresses" list (used as
the email's To). This lets a group also supply CC/BCC roles, so a group
selected on an email config can cover all three without the template
needing its own To/CC/BCC entries.

Revision ID: 0030_recipient_group_cc_bcc
Revises: 0029_system_settings
Create Date: 2026-07-10

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0030_recipient_group_cc_bcc'
down_revision: str | None = '0029_system_settings'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('ff_recipient_groups', sa.Column('cc_addresses', postgresql.ARRAY(sa.Text()), nullable=True))
    op.add_column('ff_recipient_groups', sa.Column('bcc_addresses', postgresql.ARRAY(sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('ff_recipient_groups', 'bcc_addresses')
    op.drop_column('ff_recipient_groups', 'cc_addresses')
