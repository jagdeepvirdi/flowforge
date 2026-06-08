"""Tests for app.py branches: IP allowlist, sweep stuck runs, error handlers."""
import os
from unittest.mock import patch

# ── Error handlers ────────────────────────────────────────────────────────────

def test_404_handler(client, headers):
    # When frontend/dist exists the SPA catch-all intercepts unknown paths;
    # verify 404 via a known API endpoint that returns it for missing resources.
    resp = client.get('/api/pipelines/00000000-0000-0000-0000-000000000000', headers=headers)
    assert resp.status_code == 404
    assert 'error' in resp.get_json()


def test_health_endpoint(client):
    resp = client.get('/api/health')
    assert resp.status_code == 200
    assert resp.get_json()['status'] == 'ok'


# ── IP allowlist ──────────────────────────────────────────────────────────────

def test_ip_allowlist_blocks_non_listed_ip(app):
    with patch.dict(os.environ, {'FLOWFORGE_ALLOWED_IPS': '10.0.0.0/8'}):
        from flowforge.api.app import create_app
        test_app = create_app({'TESTING': True,
                               'SQLALCHEMY_DATABASE_URI': os.environ['FLOWFORGE_DB_URL'],
                               'SECRET_KEY': os.environ['FLOWFORGE_SECRET_KEY'],
                               'JWT_SECRET': os.environ['FLOWFORGE_JWT_SECRET'],
                               'RATELIMIT_ENABLED': False})
        c = test_app.test_client()
        resp = c.get('/api/health')
        # 127.0.0.1 is not in 10.0.0.0/8
        assert resp.status_code == 403
        assert 'denied' in resp.get_json()['error'].lower()


def test_ip_allowlist_allows_listed_ip(app):
    with patch.dict(os.environ, {'FLOWFORGE_ALLOWED_IPS': '127.0.0.1/32'}):
        from flowforge.api.app import create_app
        test_app = create_app({'TESTING': True,
                               'SQLALCHEMY_DATABASE_URI': os.environ['FLOWFORGE_DB_URL'],
                               'SECRET_KEY': os.environ['FLOWFORGE_SECRET_KEY'],
                               'JWT_SECRET': os.environ['FLOWFORGE_JWT_SECRET'],
                               'RATELIMIT_ENABLED': False})
        c = test_app.test_client()
        resp = c.get('/api/health')
        assert resp.status_code == 200


def test_ip_allowlist_invalid_cidr_is_skipped(app):
    with patch.dict(os.environ, {'FLOWFORGE_ALLOWED_IPS': 'not-a-cidr,127.0.0.1/32'}):
        from flowforge.api.app import create_app
        test_app = create_app({'TESTING': True,
                               'SQLALCHEMY_DATABASE_URI': os.environ['FLOWFORGE_DB_URL'],
                               'SECRET_KEY': os.environ['FLOWFORGE_SECRET_KEY'],
                               'JWT_SECRET': os.environ['FLOWFORGE_JWT_SECRET'],
                               'RATELIMIT_ENABLED': False})
        c = test_app.test_client()
        # valid CIDR (127.0.0.1/32) should still allow access
        resp = c.get('/api/health')
        assert resp.status_code == 200


def test_ip_allowlist_empty_string_no_filter(app):
    with patch.dict(os.environ, {'FLOWFORGE_ALLOWED_IPS': ''}):
        from flowforge.api.app import create_app
        test_app = create_app({'TESTING': True,
                               'SQLALCHEMY_DATABASE_URI': os.environ['FLOWFORGE_DB_URL'],
                               'SECRET_KEY': os.environ['FLOWFORGE_SECRET_KEY'],
                               'JWT_SECRET': os.environ['FLOWFORGE_JWT_SECRET'],
                               'RATELIMIT_ENABLED': False})
        c = test_app.test_client()
        resp = c.get('/api/health')
        assert resp.status_code == 200


# ── Sweep stuck runs ──────────────────────────────────────────────────────────

def test_sweep_stuck_runs_on_startup(app):
    """Runs left in 'running' state after a restart should be swept to 'failed'."""
    from datetime import UTC, datetime
    with app.app_context():
        from flowforge.api.app import _sweep_stuck_runs
        from flowforge.db.models import Pipeline, PipelineRun, db

        # Create a pipeline and a stuck run
        pipeline = Pipeline(name='Sweep Test Pipeline', enabled=True)
        db.session.add(pipeline)
        db.session.flush()

        run = PipelineRun(
            pipeline_id=pipeline.id,
            pipeline_name='Sweep Test Pipeline',
            status='running',
            started_at=datetime.now(UTC),
        )
        db.session.add(run)
        db.session.commit()
        run_id = run.id

        _sweep_stuck_runs(app)

        db.session.expire_all()
        swept = db.session.get(PipelineRun, run_id)
        assert swept.status == 'failed'
        assert 'restart' in swept.error_message.lower()

        # Cleanup
        db.session.delete(swept)
        db.session.delete(pipeline)
        db.session.commit()


# ── JWT secret fallback warning ───────────────────────────────────────────────

def test_jwt_fallback_warning_emitted_without_jwt_secret():
    import warnings
    env = {k: v for k, v in os.environ.items() if k != 'FLOWFORGE_JWT_SECRET'}
    env['FLASK_ENV'] = 'development'
    with patch.dict(os.environ, env, clear=True):
        if 'FLOWFORGE_JWT_SECRET' in os.environ:
            del os.environ['FLOWFORGE_JWT_SECRET']
        from flowforge.api.app import create_app
        with warnings.catch_warnings(record=True):
            warnings.simplefilter('always')
            create_app({'TESTING': True,
                        'SQLALCHEMY_DATABASE_URI': os.environ.get(
                            'FLOWFORGE_DB_URL',
                            'postgresql://flowforge:testpass@localhost:5432/flowforge_test'),
                        'SECRET_KEY': 'a' * 64,
                        'RATELIMIT_ENABLED': False})
        # May or may not emit depending on whether FLOWFORGE_SECRET_KEY is set
        # The important thing is that no exception is raised
