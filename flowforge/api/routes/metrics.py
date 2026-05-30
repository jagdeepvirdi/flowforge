"""Prometheus-compatible metrics endpoint — GET /api/metrics."""
import os

from flask import Blueprint, Response

from flowforge.api.auth import require_auth

bp = Blueprint('metrics', __name__)


@bp.get('/metrics')
@require_auth
def metrics():
    """Return FlowForge runtime metrics in Prometheus plain-text format.

    Requires a valid Bearer token (same as all other /api endpoints).
    Configure Prometheus with bearer_token or bearer_token_file to scrape this endpoint.
    """
    text = _collect()
    return Response(text, mimetype='text/plain; version=0.0.4; charset=utf-8')


def _collect() -> str:
    from flowforge.db.models import PipelineRun, db

    lines: list[str] = []

    # ── flowforge_runs_total ────────────────────────────────────────────────────
    lines.append('# HELP flowforge_runs_total Total pipeline runs by final status.')
    lines.append('# TYPE flowforge_runs_total counter')
    for status in ('success', 'failed', 'cancelled'):
        count = db.session.query(PipelineRun).filter_by(status=status).count()
        lines.append(f'flowforge_runs_total{{status="{status}"}} {count}')

    # ── flowforge_runs_active ───────────────────────────────────────────────────
    active = db.session.query(PipelineRun).filter_by(status='running').count()
    lines.append('# HELP flowforge_runs_active Pipeline runs currently executing.')
    lines.append('# TYPE flowforge_runs_active gauge')
    lines.append(f'flowforge_runs_active {active}')

    # ── flowforge_queue_depth ───────────────────────────────────────────────────
    depth = _celery_queue_depth()
    lines.append('# HELP flowforge_queue_depth Tasks waiting in the Celery queue (0 when not using Redis).')
    lines.append('# TYPE flowforge_queue_depth gauge')
    lines.append(f'flowforge_queue_depth {depth}')

    return '\n'.join(lines) + '\n'


def _celery_queue_depth() -> int:
    """Return the number of unacknowledged Celery tasks in the default queue."""
    redis_url = os.environ.get('FLOWFORGE_REDIS_URL', '')
    if not redis_url:
        return 0
    try:
        import redis as _redis
        r = _redis.from_url(redis_url, socket_connect_timeout=2)
        return int(r.llen('celery'))
    except Exception:
        return 0
