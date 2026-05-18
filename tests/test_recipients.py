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


def test_get_group(client, headers, group_id):
    resp = client.get(f'/api/recipient-groups/{group_id}', headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['id'] == group_id


def test_update_group(client, headers, group_id):
    resp = client.put(f'/api/recipient-groups/{group_id}',
                      json={'name': 'Renamed Group',
                            'addresses': ['charlie@example.com']}, headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['name'] == 'Renamed Group'
    assert 'charlie@example.com' in data['addresses']


def test_delete_group(client, headers):
    resp = client.post('/api/recipient-groups', json=GROUP_PAYLOAD, headers=headers)
    gid = resp.get_json()['id']
    assert client.delete(f'/api/recipient-groups/{gid}', headers=headers).status_code == 200
    assert client.get(f'/api/recipient-groups/{gid}', headers=headers).status_code == 404
