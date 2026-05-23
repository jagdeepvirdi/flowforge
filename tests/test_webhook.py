"""Tests for webhook token management and the public trigger endpoint (NEW-10)."""
import hashlib
import pytest

PIPELINE_PAYLOAD = {
    'name': 'Webhook Test Pipeline',
    'description': 'Used by webhook tests',
    'enabled': True,
    'schedule': None,
}


@pytest.fixture
def pipeline_id(client, headers):
    resp = client.post('/api/pipelines', json=PIPELINE_PAYLOAD, headers=headers)
    assert resp.status_code == 201
    pid = resp.get_json()['id']
    yield pid
    client.delete(f'/api/pipelines/{pid}', headers=headers)


@pytest.fixture
def webhook_token(client, headers, pipeline_id):
    """Create a webhook token and return the raw token string."""
    resp = client.post(
        f'/api/pipelines/{pipeline_id}/webhook-tokens',
        json={'label': 'test token'},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.get_json()


# ── Token management (JWT-protected) ──────────────────────────────────────────

def test_list_tokens_empty(client, headers, pipeline_id):
    resp = client.get(f'/api/pipelines/{pipeline_id}/webhook-tokens', headers=headers)
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_list_tokens_requires_auth(client, pipeline_id):
    resp = client.get(f'/api/pipelines/{pipeline_id}/webhook-tokens')
    assert resp.status_code == 401


def test_create_token_returns_raw_token_once(client, headers, pipeline_id):
    resp = client.post(
        f'/api/pipelines/{pipeline_id}/webhook-tokens',
        json={'label': 'CI deploy hook'},
        headers=headers,
    )
    data = resp.get_json()
    assert resp.status_code == 201
    assert 'token' in data                         # raw token returned at creation
    assert data['token'].startswith('flwf_')       # recognisable prefix
    assert data['label'] == 'CI deploy hook'
    assert data['enabled'] is True
    assert 'id' in data
    assert 'last_used_at' in data


def test_create_token_requires_auth(client, pipeline_id):
    resp = client.post(f'/api/pipelines/{pipeline_id}/webhook-tokens', json={'label': 'x'})
    assert resp.status_code == 401


def test_create_token_for_missing_pipeline(client, headers):
    fake = '00000000-0000-0000-0000-000000000099'
    resp = client.post(f'/api/pipelines/{fake}/webhook-tokens', json={'label': 'x'}, headers=headers)
    assert resp.status_code == 404


def test_list_tokens_after_create(client, headers, pipeline_id, webhook_token):
    resp = client.get(f'/api/pipelines/{pipeline_id}/webhook-tokens', headers=headers)
    assert resp.status_code == 200
    tokens = resp.get_json()
    assert len(tokens) == 1
    assert tokens[0]['id'] == webhook_token['id']
    assert 'token' not in tokens[0]   # raw token NOT exposed in list


def test_raw_token_not_stored_as_plaintext(client, headers, pipeline_id, webhook_token):
    """The list endpoint must not expose the plaintext token."""
    raw = webhook_token['token']
    listed = client.get(f'/api/pipelines/{pipeline_id}/webhook-tokens', headers=headers).get_json()
    assert all('token' not in t for t in listed)
    assert all(t.get('token_hash') is None for t in listed)  # hash also not exposed


def test_token_hash_is_sha256_of_raw(client, headers, pipeline_id, webhook_token):
    raw = webhook_token['token']
    expected_hash = hashlib.sha256(raw.encode()).hexdigest()
    # Verify via DB (using Flask app context)
    from flowforge.db.models import WebhookToken, db
    with client.application.app_context():
        wt = db.session.get(WebhookToken, webhook_token['id'])
        assert wt is not None
        assert wt.token_hash == expected_hash


def test_revoke_token(client, headers, pipeline_id, webhook_token):
    tid = webhook_token['id']
    resp = client.delete(f'/api/pipelines/{pipeline_id}/webhook-tokens/{tid}', headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['deleted'] == tid

    # Token is gone from the list
    listed = client.get(f'/api/pipelines/{pipeline_id}/webhook-tokens', headers=headers).get_json()
    assert all(t['id'] != tid for t in listed)


def test_revoke_requires_auth(client, pipeline_id, webhook_token):
    tid = webhook_token['id']
    resp = client.delete(f'/api/pipelines/{pipeline_id}/webhook-tokens/{tid}')
    assert resp.status_code == 401


def test_revoke_wrong_pipeline(client, headers, pipeline_id, webhook_token):
    """Token belongs to pipeline_id; deleting via a different pipeline UUID → 404."""
    other_resp = client.post('/api/pipelines', json={**PIPELINE_PAYLOAD, 'name': 'Other pipeline'}, headers=headers)
    other_id = other_resp.get_json()['id']
    tid = webhook_token['id']
    resp = client.delete(f'/api/pipelines/{other_id}/webhook-tokens/{tid}', headers=headers)
    assert resp.status_code == 404
    client.delete(f'/api/pipelines/{other_id}', headers=headers)


# ── Public trigger endpoint ────────────────────────────────────────────────────

def test_trigger_with_valid_token_returns_202(client, pipeline_id, webhook_token):
    raw = webhook_token['token']
    resp = client.post(f'/api/pipelines/{pipeline_id}/trigger?token={raw}')
    assert resp.status_code == 202
    data = resp.get_json()
    assert data['status'] == 'running'
    assert 'run_id' in data


def test_trigger_no_token_returns_401(client, pipeline_id):
    resp = client.post(f'/api/pipelines/{pipeline_id}/trigger')
    assert resp.status_code == 401


def test_trigger_wrong_token_returns_401(client, pipeline_id):
    resp = client.post(f'/api/pipelines/{pipeline_id}/trigger?token=flwf_notarealtoken')
    assert resp.status_code == 401


def test_trigger_revoked_token_returns_401(client, headers, pipeline_id, webhook_token):
    raw = webhook_token['token']
    tid = webhook_token['id']
    client.delete(f'/api/pipelines/{pipeline_id}/webhook-tokens/{tid}', headers=headers)
    resp = client.post(f'/api/pipelines/{pipeline_id}/trigger?token={raw}')
    assert resp.status_code == 401


def test_trigger_sets_triggered_by_api(client, headers, pipeline_id, webhook_token):
    raw = webhook_token['token']
    trigger_resp = client.post(f'/api/pipelines/{pipeline_id}/trigger?token={raw}')
    assert trigger_resp.status_code == 202
    run_id = trigger_resp.get_json()['run_id']

    # Fetch the run and confirm triggered_by
    run_resp = client.get(f'/api/runs/{run_id}', headers=headers)
    assert run_resp.status_code == 200
    assert run_resp.get_json()['triggered_by'] == 'api'


def test_trigger_updates_last_used_at(client, headers, pipeline_id, webhook_token):
    raw = webhook_token['token']
    assert webhook_token['last_used_at'] is None   # freshly created

    client.post(f'/api/pipelines/{pipeline_id}/trigger?token={raw}')

    listed = client.get(f'/api/pipelines/{pipeline_id}/webhook-tokens', headers=headers).get_json()
    assert listed[0]['last_used_at'] is not None


def test_trigger_disabled_pipeline_returns_400(client, headers, pipeline_id, webhook_token):
    # Disable the pipeline
    client.put(f'/api/pipelines/{pipeline_id}', json={'enabled': False}, headers=headers)
    raw = webhook_token['token']
    resp = client.post(f'/api/pipelines/{pipeline_id}/trigger?token={raw}')
    assert resp.status_code == 400
    # Re-enable for cleanup
    client.put(f'/api/pipelines/{pipeline_id}', json={'enabled': True}, headers=headers)


def test_trigger_wrong_pipeline_id_with_valid_token(client, headers, pipeline_id, webhook_token):
    """Token for pipeline_id must not work on a different pipeline."""
    other_resp = client.post('/api/pipelines', json={**PIPELINE_PAYLOAD, 'name': 'Other pipeline 2'}, headers=headers)
    other_id = other_resp.get_json()['id']
    raw = webhook_token['token']
    resp = client.post(f'/api/pipelines/{other_id}/trigger?token={raw}')
    assert resp.status_code == 401
    client.delete(f'/api/pipelines/{other_id}', headers=headers)
