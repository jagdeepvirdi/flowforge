"""Narrow ck_db_connection_type to implemented types only.

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-23

The constraint was widened in 0003 to include mysql, mssql, snowflake
before implementations existed. The factory still raises at runtime for
those types. Remove them from the constraint so the DB and the factory
agree on what is supported. MySQL, MSSQL, and Snowflake are tracked in
the backlog (More DB Support).
"""
from collections.abc import Sequence

from alembic import op

revision: str = '0009'
down_revision: str | None = '0008'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint('ck_db_connection_type', 'ff_db_connections')
    op.create_check_constraint(
        'ck_db_connection_type',
        'ff_db_connections',
        "db_type IN ('postgresql', 'oracle')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_db_connection_type', 'ff_db_connections')
    op.create_check_constraint(
        'ck_db_connection_type',
        'ff_db_connections',
        "db_type IN ('postgresql', 'oracle', 'mysql', 'mssql', 'snowflake')",
    )
