"""Shared pytest fixtures for FlowForge tests."""
import os
import sys
import uuid
import pytest
import bcrypt
from pathlib import Path
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# FLOWFORGE_DB_URL must be set before running the test suite.
# For local dev: copy .env.test.example → .env.test, fill in credentials,
#                then run:  source .env.test && pytest
# For CI: the workflow sets it in the job env (see .github/workflows/test.yml).
# ---------------------------------------------------------------------------
if 'FLOWFORGE_DB_URL' not in os.environ:
    print(
        '\n[conftest] ERROR: FLOWFORGE_DB_URL is not set.\n'
        'Copy .env.test.example to .env.test, fill in your test DB credentials,\n'
        'then run:  source .env.test && pytest\n',
        file=sys.stderr,
    )
    sys.exit(1)

# Safety guard: refuse to wipe a database whose name doesn't contain "test".
# This prevents accidentally running the test suite against the live app DB.
_db_url = os.environ['FLOWFORGE_DB_URL']
_db_name = _db_url.rstrip('/').rsplit('/', 1)[-1].split('?')[0]
if 'test' not in _db_name.lower():
    print(
        f'\n[conftest] SAFETY ABORT: FLOWFORGE_DB_URL points to "{_db_name}".\n'
        'The test suite drops and recreates all tables. It must target a\n'
        'dedicated test database whose name contains "test" (e.g. flowforge_test).\n'
        'Set FLOWFORGE_DB_URL to your test DB and retry.\n',
        file=sys.stderr,
    )
    sys.exit(1)

# Safe dummy keys for test runs — 64 hex chars = 32 bytes
os.environ.setdefault('FLOWFORGE_SECRET_KEY', 'a' * 64)
os.environ.setdefault('FLOWFORGE_JWT_SECRET',  'b' * 64)
os.environ.setdefault('FLOWFORGE_USERNAME', 'testadmin')
os.environ.setdefault('FLOWFORGE_PASSWORD', bcrypt.hashpw(b'testpass', bcrypt.gensalt(4)).decode())

_MIGRATIONS_DIR = Path(__file__).parent.parent / 'flowforge' / 'db' / 'migrations'


@pytest.fixture(scope='session', autouse=True)
def apply_migrations():
    """Drop all FlowForge tables and reapply migrations for a clean test DB."""
    from alembic import command as alembic_cmd
    from alembic.config import Config
    from sqlalchemy import create_engine, text

    db_url = os.environ['FLOWFORGE_DB_URL']

    engine = create_engine(db_url)
    with engine.begin() as conn:
        for table in [
            'ff_step_runs', 'ff_pipeline_runs', 'ff_pipeline_variables',
            'ff_pipeline_steps', 'ff_pipelines', 'ff_email_configs',
            'ff_report_configs', 'ff_bulk_load_configs', 'ff_db_connections',
            'ff_email_providers', 'ff_recipient_groups', 'ff_projects',
            'ff_users', 'alembic_version',
        ]:
            conn.execute(text(f'DROP TABLE IF EXISTS {table} CASCADE'))
    engine.dispose()

    cfg = Config()
    cfg.set_main_option('script_location', str(_MIGRATIONS_DIR))
    alembic_cmd.upgrade(cfg, 'head')

    # Seed the test admin user so auth_token fixture can log in
    seed_engine = create_engine(db_url)
    _username = os.environ.get('FLOWFORGE_USERNAME', 'testadmin')
    _hash = bcrypt.hashpw(b'testpass', bcrypt.gensalt(4)).decode()
    with seed_engine.begin() as conn:
        conn.execute(
            text('INSERT INTO ff_users (id, username, password_hash) VALUES (:id, :u, :h)'),
            {'id': str(uuid.uuid4()), 'u': _username, 'h': _hash},
        )
    seed_engine.dispose()


@pytest.fixture(scope='session')
def app(apply_migrations):
    from flowforge.api.app import create_app
    application = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': os.environ['FLOWFORGE_DB_URL'],
        'SECRET_KEY': os.environ['FLOWFORGE_SECRET_KEY'],
        'JWT_SECRET':  os.environ['FLOWFORGE_JWT_SECRET'],
    })
    yield application


@pytest.fixture(scope='session')
def client(app):
    return app.test_client()


@pytest.fixture(scope='session')
def auth_token(client):
    """Log in once and return a Bearer token for the whole session."""
    resp = client.post('/api/auth/login', json={'username': 'testadmin', 'password': 'testpass'})
    assert resp.status_code == 200, f"Login failed: {resp.get_json()}"
    return resp.get_json()['token']


@pytest.fixture
def headers(auth_token):
    return {'Authorization': f'Bearer {auth_token}', 'Content-Type': 'application/json'}


@pytest.fixture(scope='session')
def live_db_config():
    """Parse FLOWFORGE_DB_URL so live-connection tests work in any environment."""
    url = urlparse(os.environ['FLOWFORGE_DB_URL'])
    return {
        'host': url.hostname,
        'port': url.port,
        'database': url.path.lstrip('/'),
        'username': url.username,
        'password': url.password,
    }
