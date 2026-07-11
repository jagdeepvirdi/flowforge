"""Add body_format to ff_email_configs

Email bodies were always authored as raw HTML. This adds a 'text' mode where
the body is plain text + Jinja2 (no HTML knowledge required) and gets
auto-wrapped in <p>/<br> tags at render time.

Revision ID: 0031_email_body_format
Revises: 0030_recipient_group_cc_bcc
Create Date: 2026-07-11

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0031_email_body_format'
down_revision: str | None = '0030_recipient_group_cc_bcc'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'ff_email_configs',
        sa.Column('body_format', sa.String(10), nullable=False, server_default='html'),
    )


def downgrade() -> None:
    op.drop_column('ff_email_configs', 'body_format')
