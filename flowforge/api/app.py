"""Flask application factory."""
import logging
import os
from pathlib import Path

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix

from flowforge.db.models import db

limiter = Limiter(key_func=get_remote_address, default_limits=[])

_DIST = Path(__file__).parent.parent.parent / 'frontend' / 'dist'
_DOCS = Path(__file__).parent.parent.parent / 'docs'


def create_app(config: dict | None = None) -> Flask:
    # Configure root logger from LOG_LEVEL env var — no-op if CLI already called basicConfig.
    _level = getattr(logging, os.environ.get('LOG_LEVEL', 'INFO').upper(), logging.INFO)
    logging.basicConfig(level=_level, format='%(asctime)s %(levelname)s %(name)s — %(message)s')

    app = Flask(__name__)

    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'FLOWFORGE_DB_URL', 'postgresql://flowforge:flowforge@localhost:5432/flowforge'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB — prevents OOM on large POST bodies

    # AES-256 encryption key — used exclusively by flowforge/crypto.py
    app.config['SECRET_KEY'] = os.environ.get('FLOWFORGE_SECRET_KEY', '')

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

    with app.app_context():
        _sweep_stuck_runs(app)

    return app


def _sweep_stuck_runs(app: Flask) -> None:
    """Mark any pipeline runs left in 'running' state as failed (interrupted by restart)."""
    try:
        from datetime import datetime, timezone
        from sqlalchemy.exc import OperationalError
        from flowforge.db.models import PipelineRun
        stuck = db.session.query(PipelineRun).filter_by(status='running').all()
        if not stuck:
            return
        for run in stuck:
            run.status = 'failed'
            run.error_message = 'Run interrupted by server restart'
            if not run.finished_at:
                run.finished_at = datetime.now(timezone.utc)
        db.session.commit()
        app.logger.warning('Swept %d stuck pipeline run(s) left from previous session.', len(stuck))
    except Exception:
        pass  # Migrations not yet applied or DB unreachable — skip silently


def _register_blueprints(app: Flask) -> None:
    from flowforge.api.routes.ai import bp as ai_bp
    from flowforge.api.routes.auth import bp as auth_bp
    from flowforge.api.routes.bulk_loads import bp as bulk_loads_bp
    from flowforge.api.routes.connections import bp as connections_bp
    from flowforge.api.routes.emails import bp as emails_bp
    from flowforge.api.routes.pipelines import bp as pipelines_bp
    from flowforge.api.routes.projects import bp as projects_bp
    from flowforge.api.routes.providers import bp as providers_bp
    from flowforge.api.routes.recipients import bp as recipients_bp
    from flowforge.api.routes.reports import bp as reports_bp
    from flowforge.api.routes.runs import bp as runs_bp
    from flowforge.api.routes.setup import bp as setup_bp
    from flowforge.api.routes.steps import bp as steps_bp
    from flowforge.api.routes.users import bp as users_bp

    for blueprint in (
        ai_bp, auth_bp, bulk_loads_bp, connections_bp, emails_bp, pipelines_bp, projects_bp,
        providers_bp, recipients_bp, reports_bp, runs_bp, setup_bp, steps_bp, users_bp,
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
            return jsonify({'error': 'Not found'}), 404
        if not file_path.is_file():
            return jsonify({'error': 'Not found'}), 404
        return send_from_directory(_DOCS, filename, mimetype='text/plain; charset=utf-8')

    if _DIST.is_dir():
        @app.route('/', defaults={'path': ''})
        @app.route('/<path:path>')
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
        return jsonify({'error': 'Not found'}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({'error': 'Internal server error'}), 500
