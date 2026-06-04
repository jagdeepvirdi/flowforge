"""Tests for GET /api/pipelines/cron-next (TEST-3c)."""


# ── Valid expressions ─────────────────────────────────────────────────────────

def test_cron_next_every_minute(client, headers):
    resp = client.get('/api/pipelines/cron-next?expr=* * * * *', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'next_runs' in data
    assert len(data['next_runs']) == 5


def test_cron_next_default_five_results(client, headers):
    resp = client.get('/api/pipelines/cron-next?expr=0 9 * * *', headers=headers)
    assert resp.status_code == 200
    assert len(resp.get_json()['next_runs']) == 5


def test_cron_next_n_parameter(client, headers):
    resp = client.get('/api/pipelines/cron-next?expr=* * * * *&n=3', headers=headers)
    assert resp.status_code == 200
    assert len(resp.get_json()['next_runs']) == 3


def test_cron_next_n_capped_at_ten(client, headers):
    """n is capped at 10 even if a higher value is requested."""
    resp = client.get('/api/pipelines/cron-next?expr=* * * * *&n=50', headers=headers)
    assert resp.status_code == 200
    assert len(resp.get_json()['next_runs']) <= 10


def test_cron_next_results_are_iso8601(client, headers):
    from datetime import datetime
    resp = client.get('/api/pipelines/cron-next?expr=0 8 * * 1', headers=headers)
    assert resp.status_code == 200
    for ts in resp.get_json()['next_runs']:
        # Must parse as ISO-8601 without raising
        datetime.fromisoformat(ts)


def test_cron_next_results_are_in_order(client, headers):
    resp = client.get('/api/pipelines/cron-next?expr=* * * * *', headers=headers)
    times = resp.get_json()['next_runs']
    assert times == sorted(times)


# ── Invalid expressions ───────────────────────────────────────────────────────

def test_cron_next_invalid_expression_returns_400(client, headers):
    resp = client.get('/api/pipelines/cron-next?expr=not-a-cron', headers=headers)
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_cron_next_wrong_field_count_returns_400(client, headers):
    resp = client.get('/api/pipelines/cron-next?expr=* * *', headers=headers)
    assert resp.status_code == 400


def test_cron_next_out_of_range_returns_400(client, headers):
    resp = client.get('/api/pipelines/cron-next?expr=99 * * * *', headers=headers)
    assert resp.status_code == 400


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_cron_next_missing_expr_returns_400(client, headers):
    resp = client.get('/api/pipelines/cron-next', headers=headers)
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_cron_next_empty_expr_returns_400(client, headers):
    resp = client.get('/api/pipelines/cron-next?expr=', headers=headers)
    assert resp.status_code == 400


def test_cron_next_requires_auth(client):
    resp = client.get('/api/pipelines/cron-next?expr=* * * * *')
    assert resp.status_code == 401
