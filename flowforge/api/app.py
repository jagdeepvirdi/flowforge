"""Flask application factory."""
import os
from pathlib import Path

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from flowforge.db.models import db

limiter = Limiter(key_func=get_remote_address, default_limits=[])

_DIST = Path(__file__).parent.parent.parent / 'frontend' / 'dist'


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)

    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'FLOWFORGE_DB_URL', 'postgresql://flowforge:flowforge@localhost:5432/flowforge'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('FLOWFORGE_SECRET_KEY', '')
    app.config['JWT_ALGORITHM'] = 'HS256'
    app.config['JWT_EXPIRY_HOURS'] = 24

    if config:
        app.config.update(config)

    db.init_app(app)
    limiter.init_app(app)
    CORS(app, resources={r'/api/*': {'origins': os.environ.get('FLOWFORGE_CORS_ORIGIN', 'http://localhost:5173')}})

    _register_blueprints(app)
    _register_error_handlers(app)

    with app.app_context():
        db.create_all()
        _seed_admin(app)

    return app


def _seed_admin(app: Flask) -> None:
    """Insert the admin user from env vars if ff_users is empty."""
    username = os.environ.get('FLOWFORGE_USERNAME', '').strip()
    password_hash = os.environ.get('FLOWFORGE_PASSWORD', '').strip()
    if not username or not password_hash:
        return

    from flowforge.db.models import User
    if db.session.query(User).first():
        return

    user = User(username=username, password_hash=password_hash)
    db.session.add(user)
    db.session.commit()
    app.logger.info('Admin user "%s" created from env vars.', username)


def _register_blueprints(app: Flask) -> None:
    from flowforge.api.routes.auth import bp as auth_bp
    from flowforge.api.routes.connections import bp as connections_bp
    from flowforge.api.routes.emails import bp as emails_bp
    from flowforge.api.routes.pipelines import bp as pipelines_bp
    from flowforge.api.routes.providers import bp as providers_bp
    from flowforge.api.routes.recipients import bp as recipients_bp
    from flowforge.api.routes.reports import bp as reports_bp
    from flowforge.api.routes.runs import bp as runs_bp
    from flowforge.api.routes.setup import bp as setup_bp
    from flowforge.api.routes.steps import bp as steps_bp

    for blueprint in (
        auth_bp, connections_bp, emails_bp, pipelines_bp, providers_bp,
        recipients_bp, reports_bp, runs_bp, setup_bp, steps_bp,
    ):
        app.register_blueprint(blueprint, url_prefix='/api')

    @app.get('/api/health')
    def health():
        return jsonify({'status': 'ok'})

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
