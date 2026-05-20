"""Shared pytest fixtures for FlowForge tests."""
import os
import pytest
import bcrypt
from pathlib import Path
from urllib.parse import urlparse

# Use a dedicated test database — never the production one
os.environ.setdefault('FLOWFORGE_DB_URL', 'postgresql://flowforge:harpal123@localhost:5434/flowforge_test')
os.environ.setdefault('FLOWFORGE_SECRET_KEY', 'a' * 64)   # 32 bytes hex = 64 chars
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

    # Drop all FlowForge tables (FK-safe order) so migrations start clean
    engine = create_engine(db_url)
    with engine.begin() as conn:
        for table in [
            'ff_step_runs', 'ff_pipeline_runs', 'ff_pipeline_variables',
            'ff_pipeline_steps', 'ff_pipelines', 'ff_email_configs',
            'ff_report_configs', 'ff_db_connections', 'ff_email_providers',
            'ff_recipient_groups', 'ff_users', 'alembic_version',
        ]:
            conn.execute(text(f'DROP TABLE IF EXISTS {table} CASCADE'))
    engine.dispose()

    cfg = Config()
    cfg.set_main_option('script_location', str(_MIGRATIONS_DIR))
    alembic_cmd.upgrade(cfg, 'head')


@pytest.fixture(scope='session')
def app(apply_migrations):
    from flowforge.api.app import create_app
    application = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': os.environ['FLOWFORGE_DB_URL'],
        'SECRET_KEY': os.environ['FLOWFORGE_SECRET_KEY'],
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
