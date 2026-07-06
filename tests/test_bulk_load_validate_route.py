"""Tests for the bulk-load 'Test File' preview endpoints:
POST /api/bulk-load-configs/<id>/validate and .../validate-raw."""
from unittest.mock import patch

import pytest

PREVIEW_RESULT = {
    'file_name': 'a.csv',
    'files_matched': 1,
    'columns': ['id', 'name'],
    'sample_rows': [['1', 'alice']],
    'row_count_sampled': 1,
    'warnings': [],
    'error_groups': [],
    'insert_error_summary': '',
}


@pytest.fixture
def blc_id(client, headers):
    resp = client.post('/api/bulk-load-configs', json={
        'name': 'Validate Route Bulk Load',
        'source_directory': '/data/in',
        'target_table': 'staging.import_data',
    }, headers=headers)
    assert resp.status_code == 201
    cid = resp.get_json()['id']
    yield cid
    client.delete(f'/api/bulk-load-configs/{cid}', headers=headers)


# ── /bulk-load-configs/<id>/validate ────────────────────────────────────────

def test_validate_saved_config_success(client, headers, blc_id):
    with patch('flowforge.api.routes.bulk_loads.preview_bulk_load', return_value=PREVIEW_RESULT) as mock_preview:
        resp = client.post(f'/api/bulk-load-configs/{blc_id}/validate', headers=headers)
    assert resp.status_code == 200
    assert resp.get_json() == PREVIEW_RESULT
    assert mock_preview.call_args.kwargs == {'dry_run': False}


def test_validate_saved_config_dry_run_passthrough(client, headers, blc_id):
    with patch('flowforge.api.routes.bulk_loads.preview_bulk_load', return_value=PREVIEW_RESULT) as mock_preview:
        resp = client.post(f'/api/bulk-load-configs/{blc_id}/validate', json={'dry_run': True}, headers=headers)
    assert resp.status_code == 200
    assert mock_preview.call_args.kwargs == {'dry_run': True}


def test_validate_saved_config_value_error_returns_400(client, headers, blc_id):
    with patch('flowforge.api.routes.bulk_loads.preview_bulk_load',
               side_effect=ValueError('source_directory not found: /data/in')):
        resp = client.post(f'/api/bulk-load-configs/{blc_id}/validate', headers=headers)
    assert resp.status_code == 400
    assert 'not found' in resp.get_json()['error']


def test_validate_saved_config_not_found(client, headers):
    resp = client.post(
        '/api/bulk-load-configs/00000000-0000-0000-0000-000000000000/validate',
        headers=headers,
    )
    assert resp.status_code == 404
    assert resp.get_json()['error'] == 'Bulk load config not found'


def test_validate_saved_config_requires_auth(client, blc_id):
    resp = client.post(f'/api/bulk-load-configs/{blc_id}/validate')
    assert resp.status_code == 401


# ── /bulk-load-configs/validate-raw ─────────────────────────────────────────

def test_validate_raw_config_success(client, headers):
    payload = {'source_directory': '/data/in', 'target_table': 'staging.t'}
    with patch('flowforge.api.routes.bulk_loads.preview_bulk_load', return_value=PREVIEW_RESULT) as mock_preview:
        resp = client.post('/api/bulk-load-configs/validate-raw', json=payload, headers=headers)
    assert resp.status_code == 200
    assert resp.get_json() == PREVIEW_RESULT
    mock_preview.assert_called_once_with(payload, dry_run=False)


def test_validate_raw_config_dry_run_passthrough(client, headers):
    payload = {'source_directory': '/data/in', 'target_table': 'staging.t', 'dry_run': True}
    with patch('flowforge.api.routes.bulk_loads.preview_bulk_load', return_value=PREVIEW_RESULT) as mock_preview:
        resp = client.post('/api/bulk-load-configs/validate-raw', json=payload, headers=headers)
    assert resp.status_code == 200
    mock_preview.assert_called_once_with(
        {'source_directory': '/data/in', 'target_table': 'staging.t'}, dry_run=True,
    )


def test_validate_raw_config_value_error_returns_400(client, headers):
    with patch('flowforge.api.routes.bulk_loads.preview_bulk_load',
               side_effect=ValueError('no files found')):
        resp = client.post('/api/bulk-load-configs/validate-raw', json={'source_directory': '/x'}, headers=headers)
    assert resp.status_code == 400
    assert resp.get_json()['error'] == 'no files found'


def test_validate_raw_config_empty_body_defaults_empty_dict(client, headers):
    with patch('flowforge.api.routes.bulk_loads.preview_bulk_load',
               side_effect=ValueError('source_directory is required')) as mock_preview:
        resp = client.post('/api/bulk-load-configs/validate-raw', json={}, headers=headers)
    assert resp.status_code == 400
    mock_preview.assert_called_once_with({}, dry_run=False)


def test_validate_raw_config_requires_auth(client):
    resp = client.post('/api/bulk-load-configs/validate-raw', json={'source_directory': '/x'})
    assert resp.status_code == 401
