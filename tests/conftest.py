"""Shared pytest fixtures for FlowForge tests."""
import os
import pytest
import bcrypt
from urllib.parse import urlparse

# Use a dedicated test database — never the production one
os.environ.setdefault('FLOWFORGE_DB_URL', 'postgresql://flowforge:harpal123@localhost:5434/flowforge_test')
os.environ.setdefault('FLOWFORGE_SECRET_KEY', 'a' * 64)   # 32 bytes hex = 64 chars
os.environ.setdefault('FLOWFORGE_USERNAME', 'testadmin')
os.environ.setdefault('FLOWFORGE_PASSWORD', bcrypt.hashpw(b'testpass', bcrypt.gensalt(4)).decode())


@pytest.fixture(scope='session')
def app():
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
