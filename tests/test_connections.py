"""Tests for DB connection CRUD and test endpoint."""
import pytest


DB_PAYLOAD = {
    'name': 'Test PostgreSQL',
    'db_type': 'postgresql',
    'config': {
        'host': 'localhost',
        'port': 5434,
        'database': 'flowforge',
        'username': 'flowforge',
        'password': 'harpal123',
    },
    'is_default': False,
}


@pytest.fixture
def conn_id(client, headers):
    """Create a connection and return its id; delete it after the test."""
    resp = client.post('/api/db-connections', json=DB_PAYLOAD, headers=headers)
    assert resp.status_code == 201
    cid = resp.get_json()['id']
    yield cid
    client.delete(f'/api/db-connections/{cid}', headers=headers)


# ── CRUD ──────────────────────────────────────────────────────────────────────

def test_list_connections_empty_or_more(client, headers):
    resp = client.get('/api/db-connections', headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_create_connection(client, headers):
    resp = client.post('/api/db-connections', json=DB_PAYLOAD, headers=headers)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['name'] == DB_PAYLOAD['name']
    assert data['db_type'] == 'postgresql'
    assert 'id' in data
    # Cleanup
    client.delete(f'/api/db-connections/{data["id"]}', headers=headers)


def test_create_connection_missing_name(client, headers):
    bad = {**DB_PAYLOAD, 'name': ''}
    resp = client.post('/api/db-connections', json=bad, headers=headers)
    assert resp.status_code == 400


def test_create_connection_bad_type(client, headers):
    bad = {**DB_PAYLOAD, 'db_type': 'mysql'}
    resp = client.post('/api/db-connections', json=bad, headers=headers)
    assert resp.status_code == 400


def test_get_connection(client, headers, conn_id):
    resp = client.get(f'/api/db-connections/{conn_id}', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['id'] == conn_id
    # Config returned but password masked
    assert data['config']['password'] == '***'
    assert data['config']['host'] == 'localhost'


def test_update_connection(client, headers, conn_id):
    resp = client.put(f'/api/db-connections/{conn_id}',
                      json={'name': 'Updated Name'}, headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['name'] == 'Updated Name'


def test_delete_connection(client, headers):
    resp = client.post('/api/db-connections', json=DB_PAYLOAD, headers=headers)
    cid = resp.get_json()['id']
    del_resp = client.delete(f'/api/db-connections/{cid}', headers=headers)
    assert del_resp.status_code == 200
    # Confirm gone
    get_resp = client.get(f'/api/db-connections/{cid}', headers=headers)
    assert get_resp.status_code == 404


def test_get_nonexistent_connection(client, headers):
    resp = client.get('/api/db-connections/00000000-0000-0000-0000-000000000000', headers=headers)
    assert resp.status_code == 404


# ── Test endpoint ─────────────────────────────────────────────────────────────

def test_test_connection_live(client, headers, conn_id):
    """Requires the Docker PostgreSQL to be running on port 5434."""
    resp = client.post(f'/api/db-connections/{conn_id}/test', headers=headers)
    data = resp.get_json()
    assert data.get('success') is True
    assert 'latency_ms' in data


def test_test_raw_connection(client, headers):
    resp = client.post('/api/db-connections/test-raw', json={
        'db_type': 'postgresql',
        'config': {
            'host': 'localhost', 'port': 5434,
            'database': 'flowforge', 'username': 'flowforge', 'password': 'harpal123',
        },
    }, headers=headers)
    data = resp.get_json()
    assert data.get('success') is True


def test_test_raw_bad_password(client, headers):
    resp = client.post('/api/db-connections/test-raw', json={
        'db_type': 'postgresql',
        'config': {
            'host': 'localhost', 'port': 5434,
            'database': 'flowforge', 'username': 'flowforge', 'password': 'wrongpassword',
        },
    }, headers=headers)
    data = resp.get_json()
    assert data.get('success') is False
