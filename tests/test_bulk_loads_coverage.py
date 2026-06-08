"""Tests for bulk_loads.py: update and delete (the 2 uncovered endpoints)."""
import pytest


@pytest.fixture
def blc_id(client, headers):
    resp = client.post('/api/bulk-load-configs', json={
        'name': 'Coverage Bulk Load',
        'source_directory': '/data/in',
        'target_table': 'staging.import_data',
    }, headers=headers)
    assert resp.status_code == 201
    cid = resp.get_json()['id']
    yield cid
    # delete if still around
    client.delete(f'/api/bulk-load-configs/{cid}', headers=headers)


# ── update ────────────────────────────────────────────────────────────────────

def test_update_bulk_load_config_success(client, headers, blc_id):
    resp = client.put(f'/api/bulk-load-configs/{blc_id}',
                      json={
                          'name': 'Updated Bulk Load',
                          'delimiter': '|',
                          'header_rows': 2,
                          'footer_rows': 1,
                          'load_mode': 'replace',
                          'on_no_files': 'fail',
                          'use_sqlloader': True,
                      }, headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['name'] == 'Updated Bulk Load'
    assert data['delimiter'] == '|'
    assert data['header_rows'] == 2
    assert data['footer_rows'] == 1
    assert data['load_mode'] == 'replace'
    assert data['on_no_files'] == 'fail'
    assert data['use_sqlloader'] is True


def test_update_bulk_load_config_clears_connection_id(client, headers, blc_id):
    resp = client.put(f'/api/bulk-load-configs/{blc_id}',
                      json={'connection_id': None}, headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['connection_id'] is None


def test_update_bulk_load_config_not_found(client, headers):
    resp = client.put('/api/bulk-load-configs/00000000-0000-0000-0000-000000000000',
                      json={'name': 'x'}, headers=headers)
    assert resp.status_code == 404
    assert resp.get_json()['error'] == 'Bulk load config not found'


def test_update_bulk_load_config_partial_fields(client, headers, blc_id):
    resp = client.put(f'/api/bulk-load-configs/{blc_id}',
                      json={'file_prefix': 'SALES_', 'file_prefix_exclude': 'BACKUP_'},
                      headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['file_prefix'] == 'SALES_'
    assert data['file_prefix_exclude'] == 'BACKUP_'


def test_update_bulk_load_config_column_mapping(client, headers, blc_id):
    mapping = [{'source': 'col_a', 'target': 'column_a'}, {'source': 'col_b', 'target': 'column_b'}]
    resp = client.put(f'/api/bulk-load-configs/{blc_id}',
                      json={'column_mapping': mapping}, headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['column_mapping'] == mapping


# ── delete ────────────────────────────────────────────────────────────────────

def test_delete_bulk_load_config_success(client, headers):
    resp = client.post('/api/bulk-load-configs', json={
        'name': 'Delete Me BLC',
        'source_directory': '/data/del',
        'target_table': 'staging.del',
    }, headers=headers)
    assert resp.status_code == 201
    cid = resp.get_json()['id']

    del_resp = client.delete(f'/api/bulk-load-configs/{cid}', headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.get_json()['deleted'] == cid

    get_resp = client.get(f'/api/bulk-load-configs/{cid}', headers=headers)
    assert get_resp.status_code == 404


def test_delete_bulk_load_config_not_found(client, headers):
    resp = client.delete('/api/bulk-load-configs/00000000-0000-0000-0000-000000000000',
                         headers=headers)
    assert resp.status_code == 404
    assert resp.get_json()['error'] == 'Bulk load config not found'


def test_delete_bulk_load_config_requires_auth(client, blc_id):
    resp = client.delete(f'/api/bulk-load-configs/{blc_id}')
    assert resp.status_code == 401
