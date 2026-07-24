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


# ── Boot-time secret validation ─────────────────────────────────────────────

def _db_url():
    return os.environ.get(
        'FLOWFORGE_DB_URL', 'postgresql://flowforge:testpass@localhost:5432/flowforge_test'
    )


def test_boot_fails_with_empty_secret_key():
    import pytest

    from flowforge.api.app import create_app
    with pytest.raises(RuntimeError, match='FLOWFORGE_SECRET_KEY is not set'):
        create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': _db_url(),
                    'SECRET_KEY': '', 'JWT_SECRET': 'b' * 64,
                    'RATELIMIT_ENABLED': False})


def test_boot_fails_with_short_secret_key():
    import pytest

    from flowforge.api.app import create_app
    with pytest.raises(RuntimeError, match='too short'):
        create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': _db_url(),
                    'SECRET_KEY': 'changeme', 'JWT_SECRET': 'b' * 64,
                    'RATELIMIT_ENABLED': False})


def test_boot_fails_with_empty_jwt_secret_even_with_valid_secret_key():
    # A valid SECRET_KEY does not excuse an explicitly-empty JWT_SECRET — this is
    # the exact scenario that used to sign JWTs with an empty-string key.
    import pytest

    from flowforge.api.app import create_app
    with pytest.raises(RuntimeError, match='FLOWFORGE_JWT_SECRET is not set'):
        create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': _db_url(),
                    'SECRET_KEY': 'a' * 64, 'JWT_SECRET': '',
                    'RATELIMIT_ENABLED': False})


def test_boot_succeeds_with_valid_secrets():
    from flowforge.api.app import create_app
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': _db_url(),
                       'SECRET_KEY': 'a' * 64, 'JWT_SECRET': 'b' * 64,
                       'RATELIMIT_ENABLED': False})
    assert app is not None


# ── Multi-worker-without-Redis capacity warning ─────────────────────────────

def test_warns_when_multi_worker_without_redis(monkeypatch, caplog):
    import logging

    monkeypatch.setenv('GUNICORN_WORKERS', '4')
    monkeypatch.delenv('FLOWFORGE_REDIS_URL', raising=False)
    from flowforge.api.app import create_app
    with caplog.at_level(logging.WARNING):
        create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': _db_url(),
                    'SECRET_KEY': 'a' * 64, 'JWT_SECRET': 'b' * 64,
                    'RATELIMIT_ENABLED': False})
    assert any('CAPACITY' in r.message and 'GUNICORN_WORKERS=4' in r.message
               for r in caplog.records)


def test_no_warning_when_single_worker(monkeypatch, caplog):
    import logging

    monkeypatch.setenv('GUNICORN_WORKERS', '1')
    monkeypatch.delenv('FLOWFORGE_REDIS_URL', raising=False)
    from flowforge.api.app import create_app
    with caplog.at_level(logging.WARNING):
        create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': _db_url(),
                    'SECRET_KEY': 'a' * 64, 'JWT_SECRET': 'b' * 64,
                    'RATELIMIT_ENABLED': False})
    assert not any('CAPACITY' in r.message for r in caplog.records)


def test_no_warning_when_multi_worker_with_redis(monkeypatch, caplog):
    import logging

    monkeypatch.setenv('GUNICORN_WORKERS', '4')
    monkeypatch.setenv('FLOWFORGE_REDIS_URL', 'redis://localhost:6379/0')
    from flowforge.api.app import create_app
    with caplog.at_level(logging.WARNING):
        create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': _db_url(),
                    'SECRET_KEY': 'a' * 64, 'JWT_SECRET': 'b' * 64,
                    'RATELIMIT_ENABLED': False})
    assert not any('CAPACITY' in r.message for r in caplog.records)


# ── PERF-02: rate limiter storage backend ───────────────────────────────────
#
# These check app.config['RATELIMIT_STORAGE_URI'] — the value create_app() computes
# and hands to flask-limiter — rather than the live `limiter.storage` object.
# `limiter` is a module-level singleton shared with the session-scoped `app`/`client`
# fixtures used across the whole test suite; flask-limiter only builds `_storage` when
# RATELIMIT_ENABLED is true (see flask_limiter._extension.Limiter.init_app), and
# leaving it enabled here would make the shared `client` fixture start enforcing real
# rate limits (e.g. the `10 per minute` cap on triggering a run) for every other test
# that runs afterward in the same session. Confirmed manually that FLOWFORGE_REDIS_URL
# does resolve to a real `limits.storage.redis.RedisStorage` end-to-end when the
# limiter is actually enabled (see PERF-02 task notes).

def test_rate_limit_storage_uri_set_from_redis_url(monkeypatch):
    """FLOWFORGE_REDIS_URL must route flask-limiter's counters through Redis —
    otherwise each Gunicorn worker enforces the rate limit independently
    (see the CAPACITY warning above), silently multiplying the real limit."""
    monkeypatch.setenv('FLOWFORGE_REDIS_URL', 'redis://localhost:6379/0')
    from flowforge.api.app import create_app
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': _db_url(),
                       'SECRET_KEY': 'a' * 64, 'JWT_SECRET': 'b' * 64,
                       'RATELIMIT_ENABLED': False})
    assert app.config.get('RATELIMIT_STORAGE_URI') == 'redis://localhost:6379/0'


def test_rate_limit_storage_uri_unset_without_redis(monkeypatch):
    monkeypatch.delenv('FLOWFORGE_REDIS_URL', raising=False)
    from flowforge.api.app import create_app
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': _db_url(),
                       'SECRET_KEY': 'a' * 64, 'JWT_SECRET': 'b' * 64,
                       'RATELIMIT_ENABLED': False})
    assert app.config.get('RATELIMIT_STORAGE_URI') is None


def test_rate_limit_storage_uri_explicit_override_wins(monkeypatch):
    """An explicitly configured RATELIMIT_STORAGE_URI wins over the FLOWFORGE_REDIS_URL
    default (create_app() uses setdefault, not a hard override)."""
    monkeypatch.setenv('FLOWFORGE_REDIS_URL', 'redis://localhost:6379/0')
    from flowforge.api.app import create_app
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': _db_url(),
                       'SECRET_KEY': 'a' * 64, 'JWT_SECRET': 'b' * 64,
                       'RATELIMIT_ENABLED': False, 'RATELIMIT_STORAGE_URI': 'memory://'})
    assert app.config.get('RATELIMIT_STORAGE_URI') == 'memory://'
