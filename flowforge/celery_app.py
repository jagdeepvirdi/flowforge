"""Celery application factory and Flask-context integration.

Worker entry point:
    celery -A flowforge.celery_app worker --loglevel=info

Or via the CLI:
    flowforge worker
"""
import os

from celery import Celery, Task

# Module-level Flask app reference.  Set by init_celery() in the web-server
# process; lazily created by _get_app() in worker processes.
_flask_app = None


def _get_app():
    """Return the Flask app, creating one lazily when running in a Celery worker."""
    global _flask_app
    if _flask_app is None:
        from flowforge.api.app import create_app
        _flask_app = create_app()
    return _flask_app


class FlaskTask(Task):
    """Task base class that runs each task inside a Flask application context."""

    def __call__(self, *args, **kwargs):
        with _get_app().app_context():
            return self.run(*args, **kwargs)


_redis_url = os.environ.get('FLOWFORGE_REDIS_URL', 'redis://localhost:6379/0')

celery = Celery(
    'flowforge',
    broker=_redis_url,
    backend=_redis_url,
    task_cls=FlaskTask,
    include=['flowforge.tasks'],
)

celery.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
)


def init_celery(app) -> Celery:
    """Bind the module-level Celery instance to a Flask app (web-server context).

    Call this from create_app() when FLOWFORGE_REDIS_URL is configured.
    Stores the celery instance on app.extensions['celery'].
    """
    global _flask_app
    _flask_app = app
    app.extensions['celery'] = celery
    return celery
