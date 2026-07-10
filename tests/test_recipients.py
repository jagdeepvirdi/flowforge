"""Tests for recipient group CRUD."""
import pytest

GROUP_PAYLOAD = {
    'name': 'Test Team',
    'description': 'Automated test group',
    'addresses': ['alice@example.com', 'bob@example.com'],
}


@pytest.fixture
def group_id(client, headers):
    resp = client.post('/api/recipient-groups', json=GROUP_PAYLOAD, headers=headers)
    assert resp.status_code == 201
    gid = resp.get_json()['id']
    yield gid
    client.delete(f'/api/recipient-groups/{gid}', headers=headers)


def test_list_groups(client, headers):
    resp = client.get('/api/recipient-groups', headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_create_group(client, headers):
    resp = client.post('/api/recipient-groups', json=GROUP_PAYLOAD, headers=headers)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['name'] == 'Test Team'
    assert 'alice@example.com' in data['addresses']
    client.delete(f'/api/recipient-groups/{data["id"]}', headers=headers)


def test_create_group_missing_name(client, headers):
    resp = client.post('/api/recipient-groups',
                       json={'addresses': ['x@x.com']}, headers=headers)
    assert resp.status_code == 400


def test_create_group_no_addresses_at_all_rejected(client, headers):
    resp = client.post('/api/recipient-groups',
                       json={'name': 'Empty Group'}, headers=headers)
    assert resp.status_code == 400


def test_create_group_cc_only_is_allowed(client, headers):
    """A group doesn't need To addresses — CC-only (or BCC-only) is valid."""
    resp = client.post('/api/recipient-groups',
                       json={'name': 'CC Only', 'cc_addresses': ['cc@example.com']}, headers=headers)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['addresses'] == []
    assert data['cc_addresses'] == ['cc@example.com']
    assert data['bcc_addresses'] == []
    client.delete(f'/api/recipient-groups/{data["id"]}', headers=headers)


def test_create_group_with_to_cc_bcc(client, headers):
    resp = client.post('/api/recipient-groups', json={
        'name': 'Full Group',
        'addresses': ['to@example.com'],
        'cc_addresses': ['cc@example.com'],
        'bcc_addresses': ['bcc@example.com'],
    }, headers=headers)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['addresses'] == ['to@example.com']
    assert data['cc_addresses'] == ['cc@example.com']
    assert data['bcc_addresses'] == ['bcc@example.com']
    client.delete(f'/api/recipient-groups/{data["id"]}', headers=headers)


def test_get_group(client, headers, group_id):
    resp = client.get(f'/api/recipient-groups/{group_id}', headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['id'] == group_id
    assert resp.get_json()['cc_addresses'] == []
    assert resp.get_json()['bcc_addresses'] == []


def test_update_group(client, headers, group_id):
    resp = client.put(f'/api/recipient-groups/{group_id}',
                      json={'name': 'Renamed Group',
                            'addresses': ['charlie@example.com']}, headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['name'] == 'Renamed Group'
    assert 'charlie@example.com' in data['addresses']


def test_update_group_cc_bcc(client, headers, group_id):
    resp = client.put(f'/api/recipient-groups/{group_id}',
                      json={'cc_addresses': ['cc2@example.com'], 'bcc_addresses': ['bcc2@example.com']},
                      headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['cc_addresses'] == ['cc2@example.com']
    assert data['bcc_addresses'] == ['bcc2@example.com']


def test_delete_group(client, headers):
    resp = client.post('/api/recipient-groups', json=GROUP_PAYLOAD, headers=headers)
    gid = resp.get_json()['id']
    assert client.delete(f'/api/recipient-groups/{gid}', headers=headers).status_code == 200
    assert client.get(f'/api/recipient-groups/{gid}', headers=headers).status_code == 404
