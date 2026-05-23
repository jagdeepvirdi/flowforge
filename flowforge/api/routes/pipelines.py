import hashlib
import os
import secrets
import threading

from flask import Blueprint, jsonify, request

from flowforge.api.app import limiter
from flowforge.api.auth import require_auth
from flowforge import audit
from flowforge.crypto import decrypt_value, encrypt_value
from flowforge.db.models import DEFAULT_PROJECT_ID, Pipeline, PipelineRun, PipelineVariable, Project, WebhookToken, db

bp = Blueprint('pipelines', __name__)

_semaphore: threading.Semaphore | None = None


def _get_semaphore() -> threading.Semaphore:
    global _semaphore
    if _semaphore is None:
        limit = int(os.environ.get('FLOWFORGE_MAX_CONCURRENT_RUNS', '5'))
        _semaphore = threading.Semaphore(limit)
    return _semaphore


def _validate_cron(expr: str) -> str | None:
    """Return an error string if expr is not a valid 5-field cron expression, else None."""
    if not expr:
        return None
    try:
        from apscheduler.triggers.cron import CronTrigger
        CronTrigger.from_crontab(expr)
        return None
    except Exception as e:
        return str(e)


def _next_run_iso(schedule: str | None) -> str | None:
    if not schedule:
        return None
    try:
        from datetime import datetime, timezone
        from apscheduler.triggers.cron import CronTrigger
        trigger = CronTrigger.from_crontab(schedule, timezone='UTC')
        now = datetime.now(timezone.utc)
        t = trigger.get_next_fire_time(now, now)
        return t.isoformat() if t else None
    except Exception:
        return None


def _default_project_id() -> str:
    p = db.session.query(Project).filter_by(is_default=True).first()
    return p.id if p else DEFAULT_PROJECT_ID


def _pipeline_dict(p: Pipeline) -> dict:
    return {
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'schedule': p.schedule,
        'next_run': _next_run_iso(p.schedule),
        'enabled': p.enabled,
        'timeout_minutes': p.timeout_minutes,
        'project_id': p.project_id,
        'created_at': p.created_at.isoformat() if p.created_at else None,
        'updated_at': p.updated_at.isoformat() if p.updated_at else None,
        'steps': [
            {
                'id': s.id,
                'step_order': s.step_order,
                'name': s.name,
                'step_type': s.step_type,
                'config': s.config,
                'on_error': s.on_error,
                'enabled': s.enabled,
            }
            for s in p.steps
        ],
        'variables': [
            {
                'id': v.id,
                'var_key': v.var_key,
                'var_value': '***' if v.is_secret else v.var_value,
                'is_secret': v.is_secret,
            }
            for v in p.variables
        ],
    }


@bp.get('/pipelines')
@require_auth
def list_pipelines():
    query = db.session.query(Pipeline).order_by(Pipeline.name)
    project_id = request.args.get('project_id')
    if project_id:
        query = query.filter(Pipeline.project_id == project_id)
    return jsonify([_pipeline_dict(p) for p in query.all()])


@bp.get('/pipelines/cron-next')
@require_auth
def cron_next_runs():
    expr = request.args.get('expr', '').strip()
    n = min(int(request.args.get('n', 5)), 10)
    if not expr:
        return jsonify({'error': 'expr is required'}), 400
    err = _validate_cron(expr)
    if err:
        return jsonify({'error': err}), 400
    try:
        from datetime import datetime, timezone
        from apscheduler.triggers.cron import CronTrigger
        trigger = CronTrigger.from_crontab(expr, timezone='UTC')
        times, t = [], datetime.now(timezone.utc)
        for _ in range(n):
            t = trigger.get_next_fire_time(t, t)
            if t is None:
                break
            times.append(t.isoformat())
        return jsonify({'next_runs': times})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@bp.post('/pipelines')
@require_auth
def create_pipeline():
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': 'name is required'}), 400

    if data.get('schedule'):
        err = _validate_cron(data['schedule'])
        if err:
            return jsonify({'error': f'Invalid cron expression: {err}'}), 400

    pipeline = Pipeline(
        name=data['name'],
        description=data.get('description', ''),
        schedule=data.get('schedule'),
        enabled=data.get('enabled', True),
        timeout_minutes=data.get('timeout_minutes', 60),
        project_id=data.get('project_id') or _default_project_id(),
    )
    db.session.add(pipeline)
    db.session.flush()

    for var in data.get('variables', []):
        is_secret = var.get('is_secret', False)
        raw_value = var['var_value']
        db.session.add(PipelineVariable(
            pipeline_id=pipeline.id,
            var_key=var['var_key'],
            var_value=encrypt_value(raw_value) if is_secret else raw_value,
            is_secret=is_secret,
        ))

    db.session.commit()
    return jsonify(_pipeline_dict(pipeline)), 201


@bp.get('/pipelines/<uuid:pipeline_id>')
@require_auth
def get_pipeline(pipeline_id):
    pipeline = db.session.get(Pipeline, str(pipeline_id))
    if not pipeline:
        return jsonify({'error': 'Pipeline not found'}), 404
    return jsonify(_pipeline_dict(pipeline))


@bp.put('/pipelines/<uuid:pipeline_id>')
@require_auth
def update_pipeline(pipeline_id):
    pipeline = db.session.get(Pipeline, str(pipeline_id))
    if not pipeline:
        return jsonify({'error': 'Pipeline not found'}), 404

    data = request.get_json() or {}
    if data.get('schedule'):
        err = _validate_cron(data['schedule'])
        if err:
            return jsonify({'error': f'Invalid cron expression: {err}'}), 400

    for field in ('name', 'description', 'schedule', 'enabled', 'timeout_minutes', 'project_id'):
        if field in data:
            setattr(pipeline, field, data[field])

    if 'variables' in data:
        # Full replace: delete existing vars and re-create from the incoming list
        for v in pipeline.variables:
            db.session.delete(v)
        db.session.flush()
        for var in data['variables']:
            is_secret = var.get('is_secret', False)
            raw_value = var.get('var_value', '')
            db.session.add(PipelineVariable(
                pipeline_id=pipeline.id,
                var_key=var['var_key'],
                var_value=encrypt_value(raw_value) if is_secret else raw_value,
                is_secret=is_secret,
            ))

    db.session.commit()
    return jsonify(_pipeline_dict(pipeline))


@bp.delete('/pipelines/<uuid:pipeline_id>')
@require_auth
def delete_pipeline(pipeline_id):
    pipeline = db.session.get(Pipeline, str(pipeline_id))
    if not pipeline:
        return jsonify({'error': 'Pipeline not found'}), 404
    db.session.delete(pipeline)
    db.session.commit()
    return jsonify({'deleted': str(pipeline_id)})


def _launch_run(pipeline: Pipeline, triggered_by: str):
    """Shared run-dispatch logic used by both UI trigger and webhook trigger.

    Returns a Flask response tuple (json, status_code).
    """
    import concurrent.futures
    from datetime import datetime, timezone
    from flask import current_app
    from flowforge.engine.loader import load_pipeline
    from flowforge.engine.runner import run_pipeline

    if not pipeline.enabled:
        return jsonify({'error': 'Pipeline is disabled'}), 400

    sem = _get_semaphore()
    if not sem.acquire(blocking=False):
        return jsonify({'error': 'Too many concurrent pipeline runs. Try again later.'}), 429

    run = PipelineRun(
        pipeline_id=pipeline.id,
        pipeline_name=pipeline.name,
        status='running',
        triggered_by=triggered_by,
    )
    db.session.add(run)
    db.session.commit()
    run_id = run.id

    try:
        steps, pipeline_vars, secret_keys = load_pipeline(pipeline.id)
    except Exception as e:
        run.status = 'failed'
        run.error_message = f'Failed to load pipeline: {e}'
        run.finished_at = datetime.now(timezone.utc)
        db.session.commit()
        sem.release()
        return jsonify({'error': f'Failed to load pipeline: {e}'}), 500

    app = current_app._get_current_object()
    pid = pipeline.id
    pname = pipeline.name
    timeout_minutes = pipeline.timeout_minutes or 60

    def _run_in_background():
        timeout_secs = timeout_minutes * 60

        def _run_with_ctx():
            with app.app_context():
                run_pipeline(
                    pipeline_name=pname,
                    steps=steps,
                    pipeline_vars=pipeline_vars,
                    triggered_by=triggered_by,
                    pipeline_id=pid,
                    existing_run_id=run_id,
                    secret_var_keys=secret_keys,
                )

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_run_with_ctx)
                try:
                    future.result(timeout=timeout_secs)
                except concurrent.futures.TimeoutError:
                    with app.app_context():
                        timed_out = db.session.get(PipelineRun, run_id)
                        if timed_out and timed_out.status == 'running':
                            timed_out.status = 'failed'
                            timed_out.error_message = 'Pipeline timed out'
                            timed_out.finished_at = datetime.now(timezone.utc)
                            db.session.commit()
        finally:
            sem.release()

    threading.Thread(target=_run_in_background, daemon=True).start()
    return jsonify({'run_id': run_id, 'status': 'running', 'pipeline_name': pname}), 202


@bp.post('/pipelines/<uuid:pipeline_id>/run')
@require_auth
def trigger_run(pipeline_id):
    pipeline = db.session.get(Pipeline, str(pipeline_id))
    if not pipeline:
        return jsonify({'error': 'Pipeline not found'}), 404
    return _launch_run(pipeline, triggered_by='web_ui')


@bp.get('/pipelines/<uuid:pipeline_id>/runs')
@require_auth
def pipeline_runs(pipeline_id):
    from flowforge.db.models import PipelineRun
    runs = (
        db.session.query(PipelineRun)
        .filter_by(pipeline_id=str(pipeline_id))
        .order_by(PipelineRun.started_at.desc())
        .limit(50)
        .all()
    )
    return jsonify([_run_dict(r) for r in runs])


def _run_dict(r) -> dict:
    return {
        'id': r.id,
        'pipeline_id': r.pipeline_id,
        'pipeline_name': r.pipeline_name,
        'status': r.status,
        'started_at': r.started_at.isoformat() if r.started_at else None,
        'finished_at': r.finished_at.isoformat() if r.finished_at else None,
        'duration_ms': r.duration_ms,
        'triggered_by': r.triggered_by,
        'error_step': r.error_step,
        'error_message': r.error_message,
    }


# ── Webhook / API trigger ──────────────────────────────────────────────────────

def _token_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _webhook_token_dict(t: WebhookToken, *, raw: str | None = None) -> dict:
    d = {
        'id': t.id,
        'pipeline_id': t.pipeline_id,
        'label': t.label,
        'enabled': t.enabled,
        'last_used_at': t.last_used_at.isoformat() if t.last_used_at else None,
        'created_at': t.created_at.isoformat() if t.created_at else None,
    }
    if raw is not None:
        d['token'] = raw   # returned only at creation, never stored
    return d


@bp.post('/pipelines/<uuid:pipeline_id>/trigger')
@limiter.limit('30 per minute')
def trigger_via_webhook(pipeline_id):
    """Public endpoint — no JWT; authenticated by a per-pipeline webhook token."""
    raw = request.args.get('token', '').strip()
    if not raw:
        return jsonify({'error': 'token query parameter is required'}), 401

    incoming_hash = _token_hash(raw)
    wt = (
        db.session.query(WebhookToken)
        .filter_by(pipeline_id=str(pipeline_id), token_hash=incoming_hash, enabled=True)
        .first()
    )
    if not wt:
        return jsonify({'error': 'Invalid or revoked token'}), 401

    pipeline = db.session.get(Pipeline, str(pipeline_id))
    if not pipeline:
        return jsonify({'error': 'Pipeline not found'}), 404

    # Record last use (best-effort — don't fail the trigger if this errors)
    try:
        from datetime import datetime, timezone
        wt.last_used_at = datetime.now(timezone.utc)
        db.session.commit()
    except Exception:
        db.session.rollback()

    resp, status = _launch_run(pipeline, triggered_by='api')
    if status == 202:
        run_id = resp.get_json().get('run_id', '')
        audit.log_webhook_trigger(pipeline.name, run_id, remote_addr=request.remote_addr or '')
    return resp, status


@bp.get('/pipelines/<uuid:pipeline_id>/webhook-tokens')
@require_auth
def list_webhook_tokens(pipeline_id):
    pipeline = db.session.get(Pipeline, str(pipeline_id))
    if not pipeline:
        return jsonify({'error': 'Pipeline not found'}), 404
    tokens = (
        db.session.query(WebhookToken)
        .filter_by(pipeline_id=str(pipeline_id))
        .order_by(WebhookToken.created_at)
        .all()
    )
    return jsonify([_webhook_token_dict(t) for t in tokens])


@bp.post('/pipelines/<uuid:pipeline_id>/webhook-tokens')
@require_auth
def create_webhook_token(pipeline_id):
    pipeline = db.session.get(Pipeline, str(pipeline_id))
    if not pipeline:
        return jsonify({'error': 'Pipeline not found'}), 404

    data = request.get_json(silent=True) or {}
    label = str(data.get('label', '')).strip()[:100]

    raw = 'flwf_' + secrets.token_urlsafe(32)
    wt = WebhookToken(
        pipeline_id=str(pipeline_id),
        label=label,
        token_hash=_token_hash(raw),
    )
    db.session.add(wt)
    db.session.commit()
    return jsonify(_webhook_token_dict(wt, raw=raw)), 201


@bp.delete('/pipelines/<uuid:pipeline_id>/webhook-tokens/<uuid:token_id>')
@require_auth
def revoke_webhook_token(pipeline_id, token_id):
    wt = db.session.query(WebhookToken).filter_by(
        id=str(token_id), pipeline_id=str(pipeline_id)
    ).first()
    if not wt:
        return jsonify({'error': 'Token not found'}), 404
    db.session.delete(wt)
    db.session.commit()
    return jsonify({'deleted': str(token_id)})
