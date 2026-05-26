import hashlib
import os
import secrets
import threading

from flask import Blueprint, jsonify, request

from flowforge.api.app import limiter
from flowforge.api.auth import require_auth, require_role
from flowforge.api.serializers import run_dict
from flowforge.api.validators import validate_pipeline, validate_pipeline_variable
from flowforge import audit
from flowforge.crypto import decrypt_value, encrypt_value
from flowforge.db.models import DEFAULT_PROJECT_ID, Pipeline, PipelineRun, PipelineVariable, Project, WebhookToken, db
from flowforge.engine.launcher import launch_run

bp = Blueprint('pipelines', __name__)

# ── constants ──
_NOT_FOUND = 'Pipeline not found'


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
        'on_failure_webhook_url': p.on_failure_webhook_url,
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
@require_role(['admin', 'editor'])
def create_pipeline():
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': 'name is required'}), 400

    err = validate_pipeline(data)
    if err:
        return jsonify({'error': err}), 400

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
        on_failure_webhook_url=data.get('on_failure_webhook_url'),
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
    audit.log_pipeline_change('CREATED', pipeline.name, pipeline.id)
    return jsonify(_pipeline_dict(pipeline)), 201


@bp.get('/pipelines/<uuid:pipeline_id>')
@require_auth
def get_pipeline(pipeline_id):
    pipeline = db.session.get(Pipeline, str(pipeline_id))
    if not pipeline:
        return jsonify({'error': _NOT_FOUND}), 404
    return jsonify(_pipeline_dict(pipeline))


@bp.put('/pipelines/<uuid:pipeline_id>')
@require_role(['admin', 'editor'])
def update_pipeline(pipeline_id):
    pipeline = db.session.get(Pipeline, str(pipeline_id))
    if not pipeline:
        return jsonify({'error': _NOT_FOUND}), 404

    data = request.get_json() or {}
    len_err = validate_pipeline(data)
    if len_err:
        return jsonify({'error': len_err}), 400
    if data.get('schedule'):
        err = _validate_cron(data['schedule'])
        if err:
            return jsonify({'error': f'Invalid cron expression: {err}'}), 400

    for field in ('name', 'description', 'schedule', 'enabled', 'timeout_minutes',
                  'on_failure_webhook_url', 'project_id'):
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


@bp.post('/pipelines/<uuid:pipeline_id>/clone')
@require_role(['admin', 'editor'])
def clone_pipeline(pipeline_id):
    from flowforge.db.models import PipelineStep
    src = db.session.get(Pipeline, str(pipeline_id))
    if not src:
        return jsonify({'error': _NOT_FOUND}), 404

    # Find a unique name with (Copy) suffix
    base_name = f"{src.name} (Copy)"
    candidate = base_name
    n = 1
    while db.session.query(Pipeline).filter_by(name=candidate).first():
        n += 1
        candidate = f"{base_name} {n}"

    clone = Pipeline(
        name=candidate,
        description=src.description,
        schedule=None,           # clones start disabled with no schedule
        enabled=False,
        timeout_minutes=src.timeout_minutes,
        on_failure_webhook_url=src.on_failure_webhook_url,
        project_id=src.project_id,
    )
    db.session.add(clone)
    db.session.flush()

    for s in src.steps:
        db.session.add(PipelineStep(
            pipeline_id=clone.id,
            step_order=s.step_order,
            name=s.name,
            step_type=s.step_type,
            config=dict(s.config),
            on_error=s.on_error,
            enabled=s.enabled,
        ))

    for v in src.variables:
        db.session.add(PipelineVariable(
            pipeline_id=clone.id,
            var_key=v.var_key,
            var_value=v.var_value,
            is_secret=v.is_secret,
        ))

    db.session.commit()
    audit.log_pipeline_change('CLONED', clone.name, clone.id)
    return jsonify(_pipeline_dict(clone)), 201


@bp.delete('/pipelines/<uuid:pipeline_id>')
@require_role(['admin', 'editor'])
def delete_pipeline(pipeline_id):
    pipeline = db.session.get(Pipeline, str(pipeline_id))
    if not pipeline:
        return jsonify({'error': _NOT_FOUND}), 404
    db.session.delete(pipeline)
    db.session.commit()
    return jsonify({'deleted': str(pipeline_id)})


@bp.get('/pipelines/<uuid:pipeline_id>/export')
@require_auth
def export_pipeline(pipeline_id):
    """Return the pipeline as a YAML document suitable for re-import."""
    import io
    import yaml
    from flask import Response
    pipeline = db.session.get(Pipeline, str(pipeline_id))
    if not pipeline:
        return jsonify({'error': _NOT_FOUND}), 404

    doc = {
        'name': pipeline.name,
        'description': pipeline.description or '',
        'schedule': pipeline.schedule,
        'enabled': pipeline.enabled,
        'timeout_minutes': pipeline.timeout_minutes,
        'on_failure_webhook_url': pipeline.on_failure_webhook_url,
        'steps': [
            {
                'name': s.name,
                'step_type': s.step_type,
                'step_order': s.step_order,
                'config': dict(s.config),
                'on_error': s.on_error,
                'enabled': s.enabled,
            }
            for s in pipeline.steps
        ],
        'variables': [
            {
                'var_key': v.var_key,
                'var_value': '***' if v.is_secret else v.var_value,
                'is_secret': v.is_secret,
            }
            for v in pipeline.variables
        ],
    }
    buf = io.StringIO()
    yaml.dump(doc, buf, default_flow_style=False, allow_unicode=True, sort_keys=False)
    filename = pipeline.name.replace(' ', '_') + '.yaml'
    return Response(
        buf.getvalue(),
        mimetype='application/x-yaml',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@bp.post('/pipelines/import')
@require_role(['admin', 'editor'])
def import_pipeline():
    """Create a new pipeline from a YAML document (multipart file or JSON body with yaml_content)."""
    import yaml
    from flowforge.db.models import PipelineStep

    raw = None
    if request.content_type and 'multipart' in request.content_type:
        f = request.files.get('file')
        if not f:
            return jsonify({'error': 'No file uploaded'}), 400
        raw = f.read().decode('utf-8')
    else:
        body = request.get_json(silent=True) or {}
        raw = body.get('yaml_content', '')

    if not raw:
        return jsonify({'error': 'No YAML content provided'}), 400

    try:
        doc = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        return jsonify({'error': f'Invalid YAML: {e}'}), 400

    if not isinstance(doc, dict) or not doc.get('name'):
        return jsonify({'error': 'YAML must be a mapping with a name field'}), 400

    # Ensure unique name
    base_name = str(doc['name'])
    candidate = base_name
    n = 1
    while db.session.query(Pipeline).filter_by(name=candidate).first():
        n += 1
        candidate = f"{base_name} ({n})"

    pipeline = Pipeline(
        name=candidate,
        description=doc.get('description', ''),
        schedule=doc.get('schedule'),
        enabled=doc.get('enabled', True),
        timeout_minutes=doc.get('timeout_minutes', 60),
        on_failure_webhook_url=doc.get('on_failure_webhook_url'),
        project_id=_default_project_id(),
    )
    db.session.add(pipeline)
    db.session.flush()

    for s in doc.get('steps', []):
        db.session.add(PipelineStep(
            pipeline_id=pipeline.id,
            step_order=int(s.get('step_order', 1)),
            name=str(s['name']),
            step_type=str(s['step_type']),
            config=s.get('config') or {},
            on_error=s.get('on_error', 'stop'),
            enabled=s.get('enabled', True),
        ))

    for v in doc.get('variables', []):
        if v.get('is_secret') and v.get('var_value') == '***':
            continue   # skip masked secrets from export — user must re-enter
        db.session.add(PipelineVariable(
            pipeline_id=pipeline.id,
            var_key=str(v['var_key']),
            var_value=str(v.get('var_value', '')),
            is_secret=bool(v.get('is_secret', False)),
        ))

    db.session.commit()
    return jsonify(_pipeline_dict(pipeline)), 201


@bp.post('/pipelines/<uuid:pipeline_id>/run')
@require_role(['admin', 'editor'])
@limiter.limit('10 per minute')
def trigger_run(pipeline_id):
    pipeline = db.session.get(Pipeline, str(pipeline_id))
    if not pipeline:
        return jsonify({'error': _NOT_FOUND}), 404
    res, code = launch_run(pipeline, triggered_by='web_ui')
    return jsonify(res), code


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
    return jsonify([run_dict(r) for r in runs])


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
        return jsonify({'error': _NOT_FOUND}), 404

    # Record last use (best-effort — don't fail the trigger if this errors)
    try:
        from datetime import datetime, timezone
        wt.last_used_at = datetime.now(timezone.utc)
        db.session.commit()
    except Exception:
        db.session.rollback()

    resp, status = launch_run(pipeline, triggered_by='api')
    if status == 202:
        run_id = resp.get('run_id', '')
        audit.log_webhook_trigger(pipeline.name, run_id, remote_addr=request.remote_addr or '')
    return jsonify(resp), status


@bp.get('/pipelines/<uuid:pipeline_id>/webhook-tokens')
@require_auth
def list_webhook_tokens(pipeline_id):
    pipeline = db.session.get(Pipeline, str(pipeline_id))
    if not pipeline:
        return jsonify({'error': _NOT_FOUND}), 404
    tokens = (
        db.session.query(WebhookToken)
        .filter_by(pipeline_id=str(pipeline_id))
        .order_by(WebhookToken.created_at)
        .all()
    )
    return jsonify([_webhook_token_dict(t) for t in tokens])


@bp.post('/pipelines/<uuid:pipeline_id>/webhook-tokens')
@require_role(['admin', 'editor'])
def create_webhook_token(pipeline_id):
    pipeline = db.session.get(Pipeline, str(pipeline_id))
    if not pipeline:
        return jsonify({'error': _NOT_FOUND}), 404

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
@require_role(['admin', 'editor'])
def revoke_webhook_token(pipeline_id, token_id):
    wt = db.session.query(WebhookToken).filter_by(
        id=str(token_id), pipeline_id=str(pipeline_id)
    ).first()
    if not wt:
        return jsonify({'error': 'Token not found'}), 404
    db.session.delete(wt)
    db.session.commit()
    return jsonify({'deleted': str(token_id)})

