"""Tests for report config CRUD and query preview."""
import pytest


REPORT_PAYLOAD = {
    'name': 'Test Report',
    'description': 'Automated test report',
    'query': 'SELECT 1 AS num, now() AS ts',
    'format': 'csv',
    'output_filename': 'test_{{ current_date }}.csv',
}


@pytest.fixture
def report_id(client, headers):
    resp = client.post('/api/report-configs', json=REPORT_PAYLOAD, headers=headers)
    assert resp.status_code == 201
    rid = resp.get_json()['id']
    yield rid
    client.delete(f'/api/report-configs/{rid}', headers=headers)


@pytest.fixture
def conn_id(client, headers):
    """A live DB connection for preview tests."""
    resp = client.post('/api/db-connections', json={
        'name': 'Test DB for Reports',
        'db_type': 'postgresql',
        'config': {'host': 'localhost', 'port': 5434, 'database': 'flowforge',
                   'username': 'flowforge', 'password': 'harpal123'},
    }, headers=headers)
    cid = resp.get_json()['id']
    yield cid
    client.delete(f'/api/db-connections/{cid}', headers=headers)


# ── CRUD ──────────────────────────────────────────────────────────────────────

def test_list_reports(client, headers):
    resp = client.get('/api/report-configs', headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_create_report(client, headers):
    resp = client.post('/api/report-configs', json=REPORT_PAYLOAD, headers=headers)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['name'] == 'Test Report'
    assert data['format'] == 'csv'
    client.delete(f'/api/report-configs/{data["id"]}', headers=headers)


def test_create_report_missing_name(client, headers):
    bad = {**REPORT_PAYLOAD, 'name': ''}
    resp = client.post('/api/report-configs', json=bad, headers=headers)
    assert resp.status_code == 400


def test_create_report_bad_format(client, headers):
    bad = {**REPORT_PAYLOAD, 'format': 'docx'}
    resp = client.post('/api/report-configs', json=bad, headers=headers)
    assert resp.status_code == 400


def test_get_report(client, headers, report_id):
    resp = client.get(f'/api/report-configs/{report_id}', headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['id'] == report_id


def test_update_report(client, headers, report_id):
    resp = client.put(f'/api/report-configs/{report_id}',
                      json={'name': 'Renamed Report'}, headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['name'] == 'Renamed Report'


def test_delete_report(client, headers):
    resp = client.post('/api/report-configs', json=REPORT_PAYLOAD, headers=headers)
    rid = resp.get_json()['id']
    assert client.delete(f'/api/report-configs/{rid}', headers=headers).status_code == 200
    assert client.get(f'/api/report-configs/{rid}', headers=headers).status_code == 404


# ── Preview ───────────────────────────────────────────────────────────────────

def test_preview_report(client, headers, conn_id):
    """Run a simple SELECT via preview endpoint — requires live DB."""
    resp = client.post('/api/report-configs', json={
        **REPORT_PAYLOAD,
        'connection_id': conn_id,
        'query': 'SELECT 42 AS answer',
    }, headers=headers)
    rid = resp.get_json()['id']

    prev = client.post(f'/api/report-configs/{rid}/preview', headers=headers)
    assert prev.status_code == 200
    data = prev.get_json()
    assert 'rows' in data
    assert len(data['rows']) >= 1

    client.delete(f'/api/report-configs/{rid}', headers=headers)


def test_preview_strips_semicolon(client, headers, conn_id):
    """Query ending in semicolon must not cause syntax error."""
    resp = client.post('/api/report-configs', json={
        **REPORT_PAYLOAD,
        'connection_id': conn_id,
        'query': 'SELECT 1 AS n;',
    }, headers=headers)
    rid = resp.get_json()['id']

    prev = client.post(f'/api/report-configs/{rid}/preview', headers=headers)
    assert prev.status_code == 200

    client.delete(f'/api/report-configs/{rid}', headers=headers)
