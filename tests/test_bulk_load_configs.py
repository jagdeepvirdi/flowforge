"""Tests for bulk-load config CRUD API (/api/bulk-load-configs)."""
import pytest

PAYLOAD = {
    'name': 'Test Bulk Load',
    'description': 'Automated test bulk load config',
    'source_directory': '/tmp/test_incoming',
    'target_table': 'public.test_bulk',
}


@pytest.fixture
def bulk_cfg_id(client, headers):
    resp = client.post('/api/bulk-load-configs', json=PAYLOAD, headers=headers)
    assert resp.status_code == 201
    cid = resp.get_json()['id']
    yield cid
    client.delete(f'/api/bulk-load-configs/{cid}', headers=headers)


# ── CRUD ───────────────────────────────────────────────────────────────────────

def test_list_bulk_load_configs(client, headers):
    resp = client.get('/api/bulk-load-configs', headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_create_bulk_load_config(client, headers):
    resp = client.post('/api/bulk-load-configs', json=PAYLOAD, headers=headers)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['name'] == 'Test Bulk Load'
    assert data['target_table'] == 'public.test_bulk'
    assert 'id' in data
    client.delete(f'/api/bulk-load-configs/{data["id"]}', headers=headers)


def test_create_missing_name(client, headers):
    bad = {**PAYLOAD, 'name': ''}
    resp = client.post('/api/bulk-load-configs', json=bad, headers=headers)
    assert resp.status_code == 400


def test_create_missing_source_directory(client, headers):
    bad = {k: v for k, v in PAYLOAD.items() if k != 'source_directory'}
    resp = client.post('/api/bulk-load-configs', json=bad, headers=headers)
    assert resp.status_code == 400


def test_create_missing_target_table(client, headers):
    bad = {k: v for k, v in PAYLOAD.items() if k != 'target_table'}
    resp = client.post('/api/bulk-load-configs', json=bad, headers=headers)
    assert resp.status_code == 400


def test_get_bulk_load_config(client, headers, bulk_cfg_id):
    resp = client.get(f'/api/bulk-load-configs/{bulk_cfg_id}', headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['id'] == bulk_cfg_id


def test_get_bulk_load_config_not_found(client, headers):
    resp = client.get(
        '/api/bulk-load-configs/00000000-0000-0000-0000-000000000000',
        headers=headers,
    )
    assert resp.status_code == 404


def test_update_bulk_load_config(client, headers, bulk_cfg_id):
    resp = client.put(
        f'/api/bulk-load-configs/{bulk_cfg_id}',
        json={'name': 'Renamed Bulk Load'},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.get_json()['name'] == 'Renamed Bulk Load'


def test_update_target_table(client, headers, bulk_cfg_id):
    resp = client.put(
        f'/api/bulk-load-configs/{bulk_cfg_id}',
        json={'target_table': 'staging.new_table'},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.get_json()['target_table'] == 'staging.new_table'


def test_delete_bulk_load_config(client, headers):
    resp = client.post('/api/bulk-load-configs', json=PAYLOAD, headers=headers)
    assert resp.status_code == 201
    cid = resp.get_json()['id']
    assert client.delete(f'/api/bulk-load-configs/{cid}', headers=headers).status_code == 200
    assert client.get(f'/api/bulk-load-configs/{cid}', headers=headers).status_code == 404


# ── Defaults ───────────────────────────────────────────────────────────────────

def test_default_fields_applied(client, headers):
    """Omitting optional fields should produce sensible defaults."""
    resp = client.post('/api/bulk-load-configs', json=PAYLOAD, headers=headers)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['header_rows'] == 1
    assert data['footer_rows'] == 0
    assert data['file_type'] == 'csv'
    assert data['delimiter'] == ','
    assert data['load_mode'] == 'append'
    assert data['on_no_files'] == 'skip'
    assert data['use_sqlloader'] is False
    assert data['column_mapping'] == []
    assert data['file_prefix'] == ''
    assert data['file_prefix_exclude'] == ''
    client.delete(f'/api/bulk-load-configs/{data["id"]}', headers=headers)


def test_column_mapping_stored_and_returned(client, headers):
    mapping = [
        {'source': 'FIRST_NAME', 'target': 'first_name'},
        {'source': 'LAST_NAME',  'target': 'last_name'},
    ]
    resp = client.post(
        '/api/bulk-load-configs',
        json={**PAYLOAD, 'column_mapping': mapping},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['column_mapping'] == mapping
    client.delete(f'/api/bulk-load-configs/{data["id"]}', headers=headers)


def test_optional_fields_stored(client, headers):
    """Non-default optional fields are stored and returned correctly."""
    extra = {
        **PAYLOAD,
        'file_prefix': 'SUBS_',
        'file_prefix_exclude': 'SUBS_SKIP_',
        'file_type': 'txt',
        'delimiter': '|',
        'header_rows': 2,
        'footer_rows': 3,
        'load_mode': 'replace',
        'use_sqlloader': True,
        'archive_directory': '/archive/{{ current_date }}',
        'on_no_files': 'fail',
    }
    resp = client.post('/api/bulk-load-configs', json=extra, headers=headers)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['file_prefix'] == 'SUBS_'
    assert data['file_prefix_exclude'] == 'SUBS_SKIP_'
    assert data['delimiter'] == '|'
    assert data['header_rows'] == 2
    assert data['footer_rows'] == 3
    assert data['load_mode'] == 'replace'
    assert data['use_sqlloader'] is True
    assert data['on_no_files'] == 'fail'
    client.delete(f'/api/bulk-load-configs/{data["id"]}', headers=headers)
