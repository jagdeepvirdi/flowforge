"""Add Snowflake/BigQuery/Redshift connection types

Revision ID: 0027_snowflake_bigquery_redshift
Revises: 0026_relax_step_type_constraint
Create Date: 2026-07-01

"""
from collections.abc import Sequence

from alembic import op

revision: str = '0027_snowflake_bigquery_redshift'
down_revision: str | None = '0026_relax_step_type_constraint'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_DB_TYPES = "'postgresql', 'oracle', 'mysql', 'mssql', 'odbc'"
_NEW_DB_TYPES = "'postgresql', 'oracle', 'mysql', 'mssql', 'odbc', 'redshift', 'snowflake', 'bigquery'"


def upgrade() -> None:
    op.drop_constraint('ck_db_connection_type', 'ff_db_connections')
    op.create_check_constraint(
        'ck_db_connection_type', 'ff_db_connections',
        f'db_type IN ({_NEW_DB_TYPES})',
    )


def downgrade() -> None:
    op.drop_constraint('ck_db_connection_type', 'ff_db_connections')
    op.create_check_constraint(
        'ck_db_connection_type', 'ff_db_connections',
        f'db_type IN ({_OLD_DB_TYPES})',
    )
