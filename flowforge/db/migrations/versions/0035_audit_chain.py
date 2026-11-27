"""Tamper-evident audit log: hash-chain columns and a trigger that blocks edits

Revision ID: 0035_audit_chain
Revises: 0034_token_map
Create Date: 2026-11-27

The trigger refuses UPDATE, DELETE and TRUNCATE on ff_audit_log unless the transaction has set
flowforge.audit_maintenance = 'on' (only the retention prune and the GDPR purge do). It stops
accidents and application-level exploits; a database owner can still drop it, which is what the
hash chain (flowforge/audit_chain.py) is for. Existing rows keep seq NULL ("legacy", unverifiable).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0035_audit_chain'
down_revision: str | None = '0034_token_map'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FUNCTION = """
CREATE OR REPLACE FUNCTION ff_audit_log_guard() RETURNS trigger AS $$
BEGIN
    IF coalesce(current_setting('flowforge.audit_maintenance', true), '') = 'on' THEN
        IF TG_OP = 'DELETE' THEN
            RETURN OLD;
        ELSIF TG_OP = 'TRUNCATE' THEN
            RETURN NULL;
        END IF;
        RETURN NEW;
    END IF;
    RAISE EXCEPTION USING
        MESSAGE = 'ff_audit_log is append-only: ' || TG_OP || ' is not allowed outside audit maintenance',
        ERRCODE = 'insufficient_privilege';
END;
$$ LANGUAGE plpgsql
"""


def upgrade() -> None:
    op.add_column('ff_audit_log', sa.Column('seq', sa.BigInteger, nullable=True))
    op.add_column('ff_audit_log', sa.Column('prev_hash', sa.String(64), nullable=True))
    op.add_column('ff_audit_log', sa.Column('content_digest', sa.String(64), nullable=True))
    op.add_column('ff_audit_log', sa.Column('row_hash', sa.String(64), nullable=True))
    op.add_column('ff_audit_log', sa.Column('anonymized', sa.Boolean, nullable=False, server_default='false'))
    op.create_unique_constraint('ff_audit_log_seq_key', 'ff_audit_log', ['seq'])   # what unique=True would be named
    op.execute(_FUNCTION)
    op.execute('CREATE TRIGGER ff_audit_log_no_modify BEFORE UPDATE OR DELETE ON ff_audit_log '
               'FOR EACH ROW EXECUTE FUNCTION ff_audit_log_guard()')
    op.execute('CREATE TRIGGER ff_audit_log_no_truncate BEFORE TRUNCATE ON ff_audit_log '
               'FOR EACH STATEMENT EXECUTE FUNCTION ff_audit_log_guard()')


def downgrade() -> None:
    op.execute('DROP TRIGGER IF EXISTS ff_audit_log_no_truncate ON ff_audit_log')
    op.execute('DROP TRIGGER IF EXISTS ff_audit_log_no_modify ON ff_audit_log')
    op.execute('DROP FUNCTION IF EXISTS ff_audit_log_guard()')
    op.drop_constraint('ff_audit_log_seq_key', 'ff_audit_log', type_='unique')
    for col in ('anonymized', 'row_hash', 'content_digest', 'prev_hash', 'seq'):
        op.drop_column('ff_audit_log', col)
