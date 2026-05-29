"""Migration smoke test — drops all FF tables and re-runs Alembic from scratch.

WARNING: Destructive. Wipes the target database completely.
Run manually only, never as part of the normal pytest suite:

    python tests/manual/migrate_reset.py

Requires FLOWFORGE_DB_URL to be set. Uses FLOWFORGE_USERNAME (default: testadmin).
"""
import os
import uuid
import bcrypt
from alembic import command as alembic_cmd
from alembic.config import Config
from sqlalchemy import create_engine, text
from pathlib import Path

db_url = os.environ['FLOWFORGE_DB_URL']
print(f"Connecting to: {db_url}")

_MIGRATIONS_DIR = Path('flowforge/db/migrations')

engine = create_engine(db_url)
with engine.begin() as conn:
    print("Dropping tables...")
    for table in [
        'ff_audit_log',
        'ff_step_runs', 'ff_pipeline_runs', 'ff_pipeline_variables',
        'ff_pipeline_steps', 'ff_webhook_tokens', 'ff_pipelines',
        'ff_email_configs', 'ff_report_configs', 'ff_bulk_load_configs',
        'ff_db_connections', 'ff_email_providers', 'ff_recipient_groups',
        'ff_projects', 'ff_users', 'ff_token_blocklist', 'alembic_version',
    ]:
        conn.execute(text(f'DROP TABLE IF EXISTS {table} CASCADE'))
engine.dispose()

cfg = Config()
cfg.set_main_option('script_location', str(_MIGRATIONS_DIR))
print("Running alembic upgrade...")
alembic_cmd.upgrade(cfg, 'head')

seed_engine = create_engine(db_url)
_username = os.environ.get('FLOWFORGE_USERNAME', 'testadmin')
_hash = bcrypt.hashpw(b'testpass', bcrypt.gensalt(4)).decode()
print(f"Seeding user {_username}...")
with seed_engine.begin() as conn:
    conn.execute(
        text('INSERT INTO ff_users (id, username, password_hash, role) VALUES (:id, :u, :h, :r)'),
        {'id': str(uuid.uuid4()), 'u': _username, 'h': _hash, 'r': 'admin'},
    )
seed_engine.dispose()
print("Done.")
