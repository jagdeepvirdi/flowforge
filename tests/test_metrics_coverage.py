"""Tests for GET /api/metrics (Prometheus endpoint)."""
from unittest.mock import MagicMock, patch


def test_metrics_requires_auth(client):
    resp = client.get('/api/metrics')
    assert resp.status_code == 401


def test_metrics_returns_prometheus_text(client, headers):
    resp = client.get('/api/metrics', headers=headers)
    assert resp.status_code == 200
    assert 'text/plain' in resp.content_type
    body = resp.data.decode()
    assert 'flowforge_runs_total' in body
    assert 'flowforge_runs_active' in body
    assert 'flowforge_queue_depth' in body


def test_metrics_contains_status_labels(client, headers):
    resp = client.get('/api/metrics', headers=headers)
    body = resp.data.decode()
    assert 'status="success"' in body
    assert 'status="failed"' in body
    assert 'status="cancelled"' in body


def test_metrics_help_and_type_lines(client, headers):
    resp = client.get('/api/metrics', headers=headers)
    body = resp.data.decode()
    assert '# HELP' in body
    assert '# TYPE' in body


def test_celery_queue_depth_no_redis():
    """Without FLOWFORGE_REDIS_URL, queue depth must return 0."""
    import os
    env = {k: v for k, v in os.environ.items() if k != 'FLOWFORGE_REDIS_URL'}
    with patch.dict(os.environ, env, clear=True):
        from flowforge.api.routes.metrics import _celery_queue_depth
        assert _celery_queue_depth() == 0


def test_celery_queue_depth_redis_error():
    """Redis connection failure must return 0 (not raise)."""
    import os
    with patch.dict(os.environ, {'FLOWFORGE_REDIS_URL': 'redis://localhost:6379'}):
        mock_redis = MagicMock()
        mock_redis.from_url.side_effect = Exception('connection refused')
        with patch.dict('sys.modules', {'redis': mock_redis}):
            from importlib import reload
            import flowforge.api.routes.metrics as m
            reload(m)
            assert m._celery_queue_depth() == 0
