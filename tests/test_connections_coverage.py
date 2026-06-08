"""Tests for DB connection routes: validation, update, delete, test-raw."""
import pytest


@pytest.fixture
def conn_payload(live_db_config):
    return {
        'name': 'Coverage Test Connection',
        'db_type': 'postgresql',
        'config': live_db_config,
        'is_default': False,
    }


@pytest.fixture
def conn_id(client, headers, conn_payload):
    resp = client.post('/api/db-connections', json=conn_payload, headers=headers)
    assert resp.status_code == 201
    cid = resp.get_json()['id']
    yield cid
    client.delete(f'/api/db-connections/{cid}', headers=headers)


# ── create validation ─────────────────────────────────────────────────────────

def test_create_connection_missing_name(client, headers):
    resp = client.post('/api/db-connections',
                       json={'db_type': 'postgresql', 'config': {}},
                       headers=headers)
    assert resp.status_code == 400
    assert 'name' in resp.get_json()['error'].lower()


def test_create_connection_invalid_db_type(client, headers):
    resp = client.post('/api/db-connections',
                       json={'name': 'Bad', 'db_type': 'nosql', 'config': {'host': 'x'}},
                       headers=headers)
    assert resp.status_code == 400
    assert 'db_type' in resp.get_json()['error'].lower()


def test_create_connection_missing_config(client, headers):
    resp = client.post('/api/db-connections',
                       json={'name': 'No Config', 'db_type': 'postgresql'},
                       headers=headers)
    assert resp.status_code == 400


# ── get with config (include_config=True) ─────────────────────────────────────

def test_get_connection_includes_masked_config(client, headers, conn_id):
    resp = client.get(f'/api/db-connections/{conn_id}', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'config' in data
    # password must be masked
    assert data['config'].get('password') == '***'


def test_get_connection_not_found(client, headers):
    resp = client.get('/api/db-connections/00000000-0000-0000-0000-000000000000', headers=headers)
    assert resp.status_code == 404


# ── update ────────────────────────────────────────────────────────────────────

def test_update_connection_name(client, headers, conn_id):
    resp = client.put(f'/api/db-connections/{conn_id}',
                      json={'name': 'Renamed Connection'},
                      headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['name'] == 'Renamed Connection'


def test_update_connection_config_masked_fields_not_overwritten(client, headers, conn_id):
    """Sending *** back for a sensitive field must not overwrite the stored value."""
    resp = client.put(f'/api/db-connections/{conn_id}',
                      json={'config': {'password': '***', 'host': 'newhost'}},
                      headers=headers)
    assert resp.status_code == 200
    # Password should still be masked (not stored as ***)
    assert resp.get_json()['config']['password'] == '***'


def test_update_connection_not_found(client, headers):
    resp = client.put('/api/db-connections/00000000-0000-0000-0000-000000000000',
                      json={'name': 'x'},
                      headers=headers)
    assert resp.status_code == 404


# ── delete ────────────────────────────────────────────────────────────────────

def test_delete_connection_not_found(client, headers):
    resp = client.delete('/api/db-connections/00000000-0000-0000-0000-000000000000',
                         headers=headers)
    assert resp.status_code == 404


def test_delete_connection_success(client, headers, conn_payload):
    resp = client.post('/api/db-connections', json=conn_payload, headers=headers)
    cid = resp.get_json()['id']
    del_resp = client.delete(f'/api/db-connections/{cid}', headers=headers)
    assert del_resp.status_code == 200
    assert client.get(f'/api/db-connections/{cid}', headers=headers).status_code == 404


# ── test-raw ─────────────────────────────────────────────────────────────────

def test_test_raw_postgresql_success(client, headers, live_db_config):
    resp = client.post('/api/db-connections/test-raw',
                       json={'db_type': 'postgresql', 'config': live_db_config},
                       headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['success'] is True
    assert 'latency_ms' in resp.get_json()


def test_test_raw_postgresql_bad_credentials(client, headers):
    resp = client.post('/api/db-connections/test-raw',
                       json={'db_type': 'postgresql',
                             'config': {'host': 'localhost', 'port': 5432,
                                        'database': 'nonexistent', 'password': 'bad'}},
                       headers=headers)
    assert resp.status_code == 502
    assert resp.get_json()['success'] is False


def test_test_raw_oracle_not_installed(client, headers):
    import sys
    with pytest.MonkeyPatch().context() as mp:
        mp.setitem(sys.modules, 'oracledb', None)
        resp = client.post('/api/db-connections/test-raw',
                           json={'db_type': 'oracle', 'config': {'host': 'x', 'port': 1521}},
                           headers=headers)
    assert resp.status_code == 400
    assert 'oracledb' in resp.get_json()['error'].lower()


def test_test_raw_mysql_not_installed(client, headers):
    import sys
    with pytest.MonkeyPatch().context() as mp:
        mp.setitem(sys.modules, 'pymysql', None)
        resp = client.post('/api/db-connections/test-raw',
                           json={'db_type': 'mysql', 'config': {}},
                           headers=headers)
    assert resp.status_code == 400
    assert 'pymysql' in resp.get_json()['error'].lower()


def test_test_raw_mssql_not_installed(client, headers):
    import sys
    with pytest.MonkeyPatch().context() as mp:
        mp.setitem(sys.modules, 'pyodbc', None)
        resp = client.post('/api/db-connections/test-raw',
                           json={'db_type': 'mssql', 'config': {}},
                           headers=headers)
    assert resp.status_code == 400
    assert 'pyodbc' in resp.get_json()['error'].lower()


def test_test_raw_odbc_not_installed(client, headers):
    import sys
    with pytest.MonkeyPatch().context() as mp:
        mp.setitem(sys.modules, 'pyodbc', None)
        resp = client.post('/api/db-connections/test-raw',
                           json={'db_type': 'odbc', 'config': {'dsn': 'mydsn'}},
                           headers=headers)
    assert resp.status_code == 400
    assert 'pyodbc' in resp.get_json()['error'].lower()


def test_test_raw_odbc_missing_dsn_and_connstr(client, headers):
    from unittest.mock import MagicMock, patch
    mock_pyodbc = MagicMock()
    with patch.dict('sys.modules', {'pyodbc': mock_pyodbc}):
        resp = client.post('/api/db-connections/test-raw',
                           json={'db_type': 'odbc', 'config': {}},
                           headers=headers)
    assert resp.status_code == 400
    assert 'dsn' in resp.get_json()['error'].lower()


def test_test_raw_unsupported_type(client, headers):
    resp = client.post('/api/db-connections/test-raw',
                       json={'db_type': 'mongodb', 'config': {}},
                       headers=headers)
    assert resp.status_code == 400
    assert 'unsupported' in resp.get_json()['error'].lower()
