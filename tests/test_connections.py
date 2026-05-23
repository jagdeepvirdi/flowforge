"""Tests for DB connection CRUD, test endpoint, and encryption round-trip (TEST-3e)."""
import pytest


@pytest.fixture
def db_payload(live_db_config):
    return {
        'name': 'Test PostgreSQL',
        'db_type': 'postgresql',
        'config': live_db_config,
        'is_default': False,
    }


@pytest.fixture
def conn_id(client, headers, db_payload):
    """Create a connection and return its id; delete it after the test."""
    resp = client.post('/api/db-connections', json=db_payload, headers=headers)
    assert resp.status_code == 201
    cid = resp.get_json()['id']
    yield cid
    client.delete(f'/api/db-connections/{cid}', headers=headers)


# ── CRUD ──────────────────────────────────────────────────────────────────────

def test_list_connections_empty_or_more(client, headers):
    resp = client.get('/api/db-connections', headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_create_connection(client, headers, db_payload):
    resp = client.post('/api/db-connections', json=db_payload, headers=headers)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['name'] == db_payload['name']
    assert data['db_type'] == 'postgresql'
    assert 'id' in data
    client.delete(f'/api/db-connections/{data["id"]}', headers=headers)


def test_create_connection_missing_name(client, headers, db_payload):
    bad = {**db_payload, 'name': ''}
    resp = client.post('/api/db-connections', json=bad, headers=headers)
    assert resp.status_code == 400


def test_create_connection_bad_type(client, headers, db_payload):
    bad = {**db_payload, 'db_type': 'sqlite'}
    resp = client.post('/api/db-connections', json=bad, headers=headers)
    assert resp.status_code == 400


# ── db_type constraint narrowed to implemented types (NEW-6) ──────────────────

@pytest.mark.parametrize('bad_type', ['mysql', 'mssql', 'snowflake'])
def test_create_connection_previously_allowed_types_now_rejected(client, headers, db_payload, bad_type):
    """mysql/mssql/snowflake were permitted by migration 0003 but removed in 0009."""
    bad = {**db_payload, 'db_type': bad_type}
    resp = client.post('/api/db-connections', json=bad, headers=headers)
    assert resp.status_code == 400
    data = resp.get_json()
    assert 'error' in data
    assert 'postgresql' in data['error'] or 'oracle' in data['error']


@pytest.mark.parametrize('good_type', ['postgresql', 'oracle'])
def test_create_connection_valid_types_accepted(client, headers, db_payload, good_type):
    """Only postgresql and oracle must be accepted."""
    payload = {**db_payload, 'db_type': good_type}
    resp = client.post('/api/db-connections', json=payload, headers=headers)
    # Oracle will 201 even without a real Oracle server — config is just stored
    assert resp.status_code == 201
    client.delete(f'/api/db-connections/{resp.get_json()["id"]}', headers=headers)


def test_get_connection(client, headers, conn_id):
    resp = client.get(f'/api/db-connections/{conn_id}', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['id'] == conn_id
    assert data['config']['password'] == '***'
    assert data['config']['host'] == 'localhost'


def test_update_connection(client, headers, conn_id):
    resp = client.put(f'/api/db-connections/{conn_id}',
                      json={'name': 'Updated Name'}, headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['name'] == 'Updated Name'


def test_delete_connection(client, headers, db_payload):
    resp = client.post('/api/db-connections', json=db_payload, headers=headers)
    cid = resp.get_json()['id']
    del_resp = client.delete(f'/api/db-connections/{cid}', headers=headers)
    assert del_resp.status_code == 200
    get_resp = client.get(f'/api/db-connections/{cid}', headers=headers)
    assert get_resp.status_code == 404


def test_get_nonexistent_connection(client, headers):
    resp = client.get('/api/db-connections/00000000-0000-0000-0000-000000000000', headers=headers)
    assert resp.status_code == 404


# ── Test endpoint ─────────────────────────────────────────────────────────────

def test_test_connection_live(client, headers, conn_id):
    resp = client.post(f'/api/db-connections/{conn_id}/test', headers=headers)
    data = resp.get_json()
    assert data.get('success') is True
    assert 'latency_ms' in data


def test_test_raw_connection(client, headers, live_db_config):
    resp = client.post('/api/db-connections/test-raw', json={
        'db_type': 'postgresql',
        'config': live_db_config,
    }, headers=headers)
    data = resp.get_json()
    assert data.get('success') is True


def test_test_raw_bad_password(client, headers, live_db_config):
    bad_config = {**live_db_config, 'password': 'wrongpassword'}
    resp = client.post('/api/db-connections/test-raw', json={
        'db_type': 'postgresql',
        'config': bad_config,
    }, headers=headers)
    data = resp.get_json()
    assert data.get('success') is False


# ── Encryption round-trip (TEST-3e) ───────────────────────────────────────────

def test_sensitive_fields_masked_in_api_response(client, headers, conn_id):
    """GET /api/db-connections/:id must mask password and any sensitive fields."""
    resp = client.get(f'/api/db-connections/{conn_id}', headers=headers)
    assert resp.status_code == 200
    cfg = resp.get_json()['config']
    assert cfg['password'] == '***', 'password must be masked in API response'
    # Non-sensitive fields are returned plaintext
    assert cfg['host'] not in ('', '***')


def test_config_stored_encrypted_in_db(app, client, headers, live_db_config):
    """The raw DB column must not contain plaintext credentials."""
    from flowforge.crypto import decrypt_config
    from flowforge.db.models import DbConnection, db

    # Create a connection with a known password
    secret_password = 'super_secret_pw_12345'
    payload = {
        'name': '__enc_test_conn__',
        'db_type': 'postgresql',
        'config': {**live_db_config, 'password': secret_password},
        'is_default': False,
    }
    resp = client.post('/api/db-connections', json=payload, headers=headers)
    assert resp.status_code == 201
    conn_id = resp.get_json()['id']

    try:
        with app.app_context():
            row = db.session.get(DbConnection, conn_id)
            # Raw column must NOT be plaintext JSON containing the password
            assert secret_password not in row.config, \
                'Plaintext password found in raw DB column — encryption not applied'
            # Decrypting must give back the original value
            decrypted = decrypt_config(row.config)
            assert decrypted['password'] == secret_password
    finally:
        client.delete(f'/api/db-connections/{conn_id}', headers=headers)
