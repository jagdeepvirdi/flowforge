"""Flask application factory."""
import ipaddress
import logging
import os
from datetime import UTC
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix

from flowforge.db.models import db

limiter = Limiter(key_func=get_remote_address, default_limits=[])

# ── constants ──
_NOT_FOUND = 'Not found'
_MIN_SECRET_LENGTH = 32  # matches the documented 64-hex-char (32-byte) FLOWFORGE_SECRET_KEY


def _validate_secret(env_var_name: str, value: str) -> None:
    """Refuse to boot with an unset or too-short secret.

    Without this, an empty FLOWFORGE_JWT_SECRET/FLOWFORGE_SECRET_KEY doesn't fail loudly —
    it silently produces JWTs signed with an empty-string key, forgeable by anyone who
    knows the algorithm (HS256, set two lines below where JWT_SECRET is assigned). The
    length floor also rejects every realistic human-typed placeholder ('changeme',
    'password', 'secret', etc. are all under 32 chars) without an entropy heuristic that
    would flag the test suite's own intentionally-simple dummy keys (conftest.py uses
    'a' * 64 / 'b' * 64 — 32+ chars, but low-entropy by design for readability).
    """
    hint = 'Generate one with: python -c "import secrets; print(secrets.token_hex(32))"'
    if not value:
        raise RuntimeError(f"{env_var_name} is not set. {hint}")
    if len(value) < _MIN_SECRET_LENGTH:
        raise RuntimeError(
            f"{env_var_name} is too short ({len(value)} chars, need at least "
            f"{_MIN_SECRET_LENGTH}). {hint}"
        )

_DIST = Path(__file__).parent.parent.parent / 'frontend' / 'dist'
_DOCS = Path(__file__).parent.parent.parent / 'docs'


def create_app(config: dict | None = None) -> Flask:
    # Configure root logger from LOG_LEVEL env var — no-op if CLI already called basicConfig.
    _level = getattr(logging, os.environ.get('LOG_LEVEL', 'INFO').upper(), logging.INFO)
    logging.basicConfig(level=_level, format='%(asctime)s %(levelname)s %(name)s — %(message)s')

    app = Flask(__name__)

    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'FLOWFORGE_DB_URL', 'postgresql://flowforge:flowforge@localhost:5432/flowforge'  # NOSONAR
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB — prevents OOM on large POST bodies

    # Connection pool tuning — tune via env vars for multi-worker Gunicorn deployments.
    # Rule of thumb: POOL_SIZE × gunicorn_workers ≤ max_connections on PostgreSQL side.
    app.config['SQLALCHEMY_POOL_SIZE']    = int(os.environ.get('SQLALCHEMY_POOL_SIZE',    '5'))
    app.config['SQLALCHEMY_MAX_OVERFLOW'] = int(os.environ.get('SQLALCHEMY_MAX_OVERFLOW', '10'))
    app.config['SQLALCHEMY_POOL_TIMEOUT'] = int(os.environ.get('SQLALCHEMY_POOL_TIMEOUT', '30'))
    app.config['SQLALCHEMY_POOL_RECYCLE'] = int(os.environ.get('SQLALCHEMY_POOL_RECYCLE', '1800'))

    # AES-256 encryption key — used exclusively by flowforge/crypto.py
    app.config['SECRET_KEY'] = os.environ.get('FLOWFORGE_SECRET_KEY', '')  # NOSONAR

    # JWT signing secret — separate from the encryption key (SEC-2)
    # Falls back to SECRET_KEY for backward compatibility; set FLOWFORGE_JWT_SECRET in production.
    jwt_secret = os.environ.get('FLOWFORGE_JWT_SECRET', '')
    if not jwt_secret:
        jwt_secret = app.config['SECRET_KEY']
        if jwt_secret and not (config or {}).get('TESTING'):
            import warnings
            warnings.warn(
                'FLOWFORGE_JWT_SECRET is not set — falling back to FLOWFORGE_SECRET_KEY for JWT '
                'signing. Set a separate FLOWFORGE_JWT_SECRET in production.',
                stacklevel=2,
            )
    app.config['JWT_SECRET'] = jwt_secret
    app.config['JWT_ALGORITHM'] = 'HS256'
    app.config['JWT_EXPIRY_HOURS'] = 24

    if config:
        app.config.update(config)

    _validate_secret('FLOWFORGE_SECRET_KEY', app.config['SECRET_KEY'])
    _validate_secret('FLOWFORGE_JWT_SECRET', app.config['JWT_SECRET'])

    # Eagerly validate the encryption key's exact format (32-byte hex or raw) at boot —
    # flowforge.crypto._key() otherwise only raises the first time something is
    # encrypted/decrypted, which can be long after startup looked successful.
    from flowforge import crypto
    crypto._key()  # noqa: SLF001 — deliberate boot-time check of the same private helper crypto.py uses internally

    # CAPACITY: without Redis, FLOWFORGE_MAX_CONCURRENT_RUNS is enforced by a
    # threading.Semaphore local to this one process (see engine/concurrency.py) —
    # correct for a single Gunicorn worker, but N workers silently give you
    # N x the configured limit, not the limit. GUNICORN_WORKERS is set as a real
    # env var (not just a shell CLI default) whenever .env.example's documented
    # value flows through — see Dockerfile / docs/RUNBOOK.md's systemd units.
    gunicorn_workers = int(os.environ.get('GUNICORN_WORKERS', '1') or '1')
    if gunicorn_workers > 1 and not os.environ.get('FLOWFORGE_REDIS_URL'):
        app.logger.warning(
            'CAPACITY: GUNICORN_WORKERS=%d with no FLOWFORGE_REDIS_URL configured — '
            'FLOWFORGE_MAX_CONCURRENT_RUNS is enforced per-process, so the real '
            'deployment-wide concurrency ceiling is up to %d x the configured limit, '
            'not the limit itself. Set FLOWFORGE_REDIS_URL for a distributed counter '
            'that holds the limit across all workers.',
            gunicorn_workers, gunicorn_workers,
        )

    # ProxyFix — unwraps X-Forwarded-For so the rate limiter sees the real client IP (SEC-3)
    # Set FLOWFORGE_TRUSTED_PROXIES=1 when running behind nginx/Traefik/ALB/etc.
    num_proxies = int(os.environ.get('FLOWFORGE_TRUSTED_PROXIES', '0'))
    if num_proxies > 0:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=num_proxies, x_proto=num_proxies, x_host=num_proxies)

    db.init_app(app)
    limiter.init_app(app)

    if os.environ.get('FLOWFORGE_REDIS_URL'):
        from flowforge.celery_app import init_celery
        init_celery(app)

    # CORS — warn loudly if FLOWFORGE_CORS_ORIGIN is not set in production (SEC-6)
    cors_origin = os.environ.get('FLOWFORGE_CORS_ORIGIN', '')
    if not cors_origin:
        flask_env = os.environ.get('FLASK_ENV', 'development')
        is_testing = (config or {}).get('TESTING', False)
        if flask_env == 'production' and not is_testing:
            app.logger.warning(
                'SECURITY: FLOWFORGE_CORS_ORIGIN is not set. '
                'All cross-origin browser requests to /api/* will be blocked. '
                'Set FLOWFORGE_CORS_ORIGIN=https://your-domain.com in production.'
            )
        cors_origin = 'http://localhost:5173'  # dev/test fallback only
    CORS(app, resources={r'/api/*': {'origins': cors_origin}})

    _register_blueprints(app)
    _register_error_handlers(app)
    _register_ip_allowlist(app)

    with app.app_context():
        _sweep_stuck_runs(app)

    return app


def _register_ip_allowlist(app: Flask) -> None:
    """If FLOWFORGE_ALLOWED_IPS is set, reject /api/* requests from non-listed IPs."""
    raw = os.environ.get('FLOWFORGE_ALLOWED_IPS', '').strip()
    if not raw:
        return

    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for cidr in raw.split(','):
        cidr = cidr.strip()
        if not cidr:
            continue
        try:
            networks.append(ipaddress.ip_network(cidr, strict=False))
        except ValueError:
            app.logger.warning('FLOWFORGE_ALLOWED_IPS: invalid CIDR %r — skipped', cidr)

    if not networks:
        return

    @app.before_request
    def _check_ip():
        if not request.path.startswith('/api/'):
            return None
        client_ip = request.remote_addr or ''
        try:
            addr = ipaddress.ip_address(client_ip)
            if not any(addr in net for net in networks):
                return jsonify({'error': 'Access denied: your IP is not allowed'}), 403
        except ValueError:
            return jsonify({'error': 'Access denied: invalid client IP'}), 403
        return None


def _sweep_stuck_runs(app: Flask) -> None:
    """Mark any pipeline runs left in 'running' state as failed (interrupted by restart)."""
    try:
        from datetime import datetime

        from flowforge.db.models import PipelineRun
        stuck = db.session.query(PipelineRun).filter_by(status='running').all()
        if not stuck:
            return
        for run in stuck:
            run.status = 'failed'
            run.error_message = 'Run interrupted by server restart'
            if not run.finished_at:
                run.finished_at = datetime.now(UTC)
        db.session.commit()
        app.logger.warning('Swept %d stuck pipeline run(s) left from previous session.', len(stuck))
    except Exception:  # nosec B110 — migrations not yet applied or DB unreachable, skip silently
        pass


def _register_blueprints(app: Flask) -> None:
    from flowforge.api.routes.ai import bp as ai_bp
    from flowforge.api.routes.audit import bp as audit_bp
    from flowforge.api.routes.auth import bp as auth_bp
    from flowforge.api.routes.bulk_loads import bp as bulk_loads_bp
    from flowforge.api.routes.connections import bp as connections_bp
    from flowforge.api.routes.emails import bp as emails_bp
    from flowforge.api.routes.metrics import bp as metrics_bp
    from flowforge.api.routes.mfa import bp as mfa_bp
    from flowforge.api.routes.password_reset import bp as password_reset_bp
    from flowforge.api.routes.pipelines import bp as pipelines_bp
    from flowforge.api.routes.projects import bp as projects_bp
    from flowforge.api.routes.providers import bp as providers_bp
    from flowforge.api.routes.recipients import bp as recipients_bp
    from flowforge.api.routes.registry import bp as registry_bp
    from flowforge.api.routes.reports import bp as reports_bp
    from flowforge.api.routes.runs import bp as runs_bp
    from flowforge.api.routes.settings import bp as settings_bp
    from flowforge.api.routes.setup import bp as setup_bp
    from flowforge.api.routes.sso import bp as sso_bp
    from flowforge.api.routes.steps import bp as steps_bp
    from flowforge.api.routes.users import bp as users_bp

    for blueprint in (
        ai_bp, audit_bp, auth_bp, bulk_loads_bp, connections_bp, emails_bp, metrics_bp,
        mfa_bp, password_reset_bp, pipelines_bp, projects_bp, providers_bp, recipients_bp,
        registry_bp, reports_bp, runs_bp, settings_bp, setup_bp, sso_bp, steps_bp, users_bp,
    ):
        app.register_blueprint(blueprint, url_prefix='/api')

    @app.get('/api/health')
    def health():
        return jsonify({'status': 'ok'})

    @app.get('/api/docs/<path:filename>')
    def serve_doc(filename):
        if not _DOCS.is_dir():
            return jsonify({'error': 'Docs not found'}), 404
        file_path = (_DOCS / filename).resolve()
        if not str(file_path).startswith(str(_DOCS.resolve())):
            return jsonify({'error': _NOT_FOUND}), 404
        if not file_path.is_file():
            return jsonify({'error': _NOT_FOUND}), 404
        return send_from_directory(_DOCS, filename, mimetype='text/plain; charset=utf-8')

    if _DIST.is_dir():
        @app.get('/', defaults={'path': ''})
        @app.get('/<path:path>')
        def serve_spa(path):
            file_path = _DIST / path
            if path and file_path.is_file():
                return send_from_directory(_DIST, path)
            return send_from_directory(_DIST, 'index.html')


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(429)
    def rate_limited(e):
        return jsonify({'error': 'Too many login attempts. Try again in a minute.'}), 429

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({'error': str(e)}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({'error': 'Unauthorized'}), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({'error': 'Forbidden'}), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': _NOT_FOUND}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({'error': 'Internal server error'}), 500
