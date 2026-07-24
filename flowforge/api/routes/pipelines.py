from datetime import UTC

from flask import Blueprint, jsonify, request
from sqlalchemy.orm import selectinload

from flowforge import audit
from flowforge.api import pipeline_service, serializers
from flowforge.api.app import limiter
from flowforge.api.auth import require_auth, require_role
from flowforge.api.project_access import ACCESS_DENIED, can_access_project, scope_query
from flowforge.api.validators import validate_pipeline
from flowforge.db.models import Pipeline, PipelineDependency, PipelineRun, Project, WebhookToken, db
from flowforge.engine.launcher import launch_run

bp = Blueprint('pipelines', __name__)

# ── constants ──
_NOT_FOUND = 'Pipeline not found'


@bp.get('/pipelines')
@require_auth
def list_pipelines():
    query = scope_query(db.session.query(Pipeline).order_by(Pipeline.name), Pipeline.project_id)
    project_id = request.args.get('project_id')
    if project_id:
        if not can_access_project(project_id):
            return jsonify(ACCESS_DENIED), 403
        query = query.filter(Pipeline.project_id == project_id)

    # Capped like /runs and /audit-logs — was previously unbounded, returning
    # every pipeline in a project with no LIMIT.
    limit  = min(int(request.args.get('limit', 500)), 500)
    offset = max(int(request.args.get('offset', 0)), 0)
    query = query.offset(offset).limit(limit)

    # PERF-01: serializers.pipeline_dict() walks steps/variables/upstream_deps/
    # downstream_deps (plus each dependency's linked Pipeline for its .name) per
    # pipeline. Left unguarded that's an N+1 cascade — up to 6 extra queries per
    # row on a list endpoint. selectinload issues one extra `WHERE id IN (...)`
    # query per relationship for the whole page instead, so the query count stays
    # fixed regardless of page size. (Not joinedload: LEFT JOINing multiple
    # one-to-many collections in a single query multiplies rows — the classic
    # collection-joinedload "cartesian explosion" — selectinload avoids that.)
    query = query.options(
        selectinload(Pipeline.steps),
        selectinload(Pipeline.variables),
        selectinload(Pipeline.upstream_deps).selectinload(PipelineDependency.upstream),
        selectinload(Pipeline.downstream_deps).selectinload(PipelineDependency.downstream),
    )

    return jsonify([serializers.pipeline_dict(p) for p in query.all()])


@bp.get('/pipelines/cron-next')
@require_auth
def cron_next_runs():
    expr = request.args.get('expr', '').strip()
    n = min(int(request.args.get('n', 5)), 10)
    if not expr:
        return jsonify({'error': 'expr is required'}), 400
    err = pipeline_service.validate_cron(expr)
    if err:
        return jsonify({'error': err}), 400
    try:
        return jsonify({'next_runs': pipeline_service.cron_next_runs(expr, n)})
    except Exception as e:
        return jsonify({'error': f"{type(e).__name__}: {e}"}), 400


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
        err = pipeline_service.validate_cron(data['schedule'])
        if err:
            return jsonify({'error': f'Invalid cron expression: {err}'}), 400

    target_project_id = data.get('project_id') or pipeline_service.default_project_id()
    if not can_access_project(target_project_id):
        return jsonify(ACCESS_DENIED), 403

    pipeline = pipeline_service.create_pipeline(data, target_project_id)
    return jsonify(serializers.pipeline_dict(pipeline)), 201


@bp.get('/pipelines/<uuid:pipeline_id>')
@require_auth
def get_pipeline(pipeline_id):
    pipeline = db.session.get(Pipeline, str(pipeline_id))
    if not pipeline:
        return jsonify({'error': _NOT_FOUND}), 404
    if not can_access_project(pipeline.project_id):
        return jsonify(ACCESS_DENIED), 403
    return jsonify(serializers.pipeline_dict(pipeline))


@bp.put('/pipelines/<uuid:pipeline_id>')
@require_role(['admin', 'editor'])
def update_pipeline(pipeline_id):
    pipeline = db.session.get(Pipeline, str(pipeline_id))
    if not pipeline:
        return jsonify({'error': _NOT_FOUND}), 404
    if not can_access_project(pipeline.project_id):
        return jsonify(ACCESS_DENIED), 403

    data = request.get_json() or {}
    len_err = validate_pipeline(data)
    if len_err:
        return jsonify({'error': len_err}), 400
    if data.get('schedule'):
        err = pipeline_service.validate_cron(data['schedule'])
        if err:
            return jsonify({'error': f'Invalid cron expression: {err}'}), 400
    if 'project_id' in data and data['project_id'] != pipeline.project_id and not can_access_project(data['project_id']):
        return jsonify(ACCESS_DENIED), 403

    pipeline = pipeline_service.update_pipeline(pipeline, data)
    return jsonify(serializers.pipeline_dict(pipeline))


@bp.post('/pipelines/<uuid:pipeline_id>/promote')
@require_role(['admin', 'editor'])
def promote_pipeline(pipeline_id):
    """Copy a pipeline to a different project (environment promotion: dev → staging → prod).

    Body: { target_project_id: str, name_suffix?: str }

    Step configs that reference IDs (connection_id, report_config_id, etc.) are copied
    as-is. Warnings are returned for any references that may not resolve in the target
    project so the user can remap them.
    """
    src = db.session.get(Pipeline, str(pipeline_id))
    if not src:
        return jsonify({'error': _NOT_FOUND}), 404
    if not can_access_project(src.project_id):
        return jsonify(ACCESS_DENIED), 403

    data = request.get_json(silent=True) or {}
    target_project_id = str(data.get('target_project_id', '')).strip()
    if not target_project_id:
        return jsonify({'error': 'target_project_id is required'}), 400
    if not can_access_project(target_project_id):
        return jsonify(ACCESS_DENIED), 403

    target_project = db.session.get(Project, target_project_id)
    if not target_project:
        return jsonify({'error': 'Target project not found'}), 404

    if target_project_id == (src.project_id or ''):
        return jsonify({'error': 'Target project must be different from the source project'}), 400

    suffix = str(data.get('name_suffix', f' ({target_project.name})')).rstrip()
    clone, warnings = pipeline_service.promote_pipeline(src, target_project, suffix)
    return jsonify({
        'pipeline': serializers.pipeline_dict(clone),
        'warnings': warnings,
    }), 201


@bp.post('/pipelines/<uuid:pipeline_id>/clone')
@require_role(['admin', 'editor'])
def clone_pipeline(pipeline_id):
    src = db.session.get(Pipeline, str(pipeline_id))
    if not src:
        return jsonify({'error': _NOT_FOUND}), 404
    if not can_access_project(src.project_id):
        return jsonify(ACCESS_DENIED), 403

    clone = pipeline_service.clone_pipeline(src)
    return jsonify(serializers.pipeline_dict(clone)), 201


@bp.delete('/pipelines/<uuid:pipeline_id>')
@require_role(['admin', 'editor'])
def delete_pipeline(pipeline_id):
    pipeline = db.session.get(Pipeline, str(pipeline_id))
    if not pipeline:
        return jsonify({'error': _NOT_FOUND}), 404
    if not can_access_project(pipeline.project_id):
        return jsonify(ACCESS_DENIED), 403
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
    if not can_access_project(pipeline.project_id):
        return jsonify(ACCESS_DENIED), 403

    doc = serializers.pipeline_export_dict(pipeline)
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

    target_project_id = pipeline_service.default_project_id()
    if not can_access_project(target_project_id):
        return jsonify(ACCESS_DENIED), 403

    pipeline = pipeline_service.import_pipeline_from_yaml(doc, target_project_id)
    return jsonify(serializers.pipeline_dict(pipeline)), 201


@bp.post('/pipelines/<uuid:pipeline_id>/run')
@require_role(['admin', 'editor'])
@limiter.limit('10 per minute')
def trigger_run(pipeline_id):
    pipeline = db.session.get(Pipeline, str(pipeline_id))
    if not pipeline:
        return jsonify({'error': _NOT_FOUND}), 404
    if not can_access_project(pipeline.project_id):
        return jsonify(ACCESS_DENIED), 403
    res, code = launch_run(pipeline, triggered_by='web_ui')
    return jsonify(res), code


@bp.get('/pipelines/<uuid:pipeline_id>/runs')
@require_auth
def pipeline_runs(pipeline_id):
    pipeline = db.session.get(Pipeline, str(pipeline_id))
    if not pipeline:
        return jsonify({'error': _NOT_FOUND}), 404
    if not can_access_project(pipeline.project_id):
        return jsonify(ACCESS_DENIED), 403
    runs = (
        db.session.query(PipelineRun)
        .filter_by(pipeline_id=str(pipeline_id))
        .order_by(PipelineRun.started_at.desc())
        .limit(50)
        .all()
    )
    return jsonify([serializers.run_dict(r) for r in runs])


# ── Webhook / API trigger ──────────────────────────────────────────────────────

@bp.post('/pipelines/<uuid:pipeline_id>/trigger')
@limiter.limit('30 per minute')
def trigger_via_webhook(pipeline_id):
    """Public endpoint — no JWT; authenticated by a per-pipeline webhook token."""
    raw = request.args.get('token', '').strip()
    if not raw:
        return jsonify({'error': 'token query parameter is required'}), 401

    incoming_hash = pipeline_service.token_hash(raw)
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
        from datetime import datetime
        wt.last_used_at = datetime.now(UTC)
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
    if not can_access_project(pipeline.project_id):
        return jsonify(ACCESS_DENIED), 403
    tokens = (
        db.session.query(WebhookToken)
        .filter_by(pipeline_id=str(pipeline_id))
        .order_by(WebhookToken.created_at)
        .all()
    )
    return jsonify([serializers.webhook_token_dict(t) for t in tokens])


@bp.post('/pipelines/<uuid:pipeline_id>/webhook-tokens')
@require_role(['admin', 'editor'])
def create_webhook_token(pipeline_id):
    pipeline = db.session.get(Pipeline, str(pipeline_id))
    if not pipeline:
        return jsonify({'error': _NOT_FOUND}), 404
    if not can_access_project(pipeline.project_id):
        return jsonify(ACCESS_DENIED), 403

    data = request.get_json(silent=True) or {}
    label = str(data.get('label', '')).strip()[:100]

    wt, raw = pipeline_service.create_webhook_token(str(pipeline_id), label)
    return jsonify(serializers.webhook_token_dict(wt, raw=raw)), 201


# ── Pipeline Dependencies ─────────────────────────────────────────────────────

@bp.get('/pipelines/<uuid:pipeline_id>/dependencies')
@require_auth
def get_dependencies(pipeline_id):
    pipeline = db.session.get(Pipeline, str(pipeline_id))
    if not pipeline:
        return jsonify({'error': _NOT_FOUND}), 404
    if not can_access_project(pipeline.project_id):
        return jsonify(ACCESS_DENIED), 403
    return jsonify({
        'upstream':   [{'dep_id': d.id, 'pipeline_id': d.upstream_id,   'pipeline_name': d.upstream.name}   for d in pipeline.upstream_deps],
        'downstream': [{'dep_id': d.id, 'pipeline_id': d.downstream_id, 'pipeline_name': d.downstream.name} for d in pipeline.downstream_deps],
    })


@bp.post('/pipelines/<uuid:pipeline_id>/dependencies')
@require_role(['admin', 'editor'])
def add_dependency(pipeline_id):
    """Add an upstream dependency: this pipeline runs after upstream_id succeeds."""
    downstream_id = str(pipeline_id)
    pipeline = db.session.get(Pipeline, downstream_id)
    if not pipeline:
        return jsonify({'error': _NOT_FOUND}), 404
    if not can_access_project(pipeline.project_id):
        return jsonify(ACCESS_DENIED), 403

    data = request.get_json(silent=True) or {}
    upstream_id = str(data.get('upstream_id', '')).strip()
    if not upstream_id:
        return jsonify({'error': 'upstream_id is required'}), 400

    dep, err, status = pipeline_service.add_dependency(downstream_id, upstream_id)
    if err:
        return jsonify({'error': err}), status
    return jsonify({'dep_id': dep.id, 'upstream_id': upstream_id, 'downstream_id': downstream_id}), status


@bp.delete('/pipelines/<uuid:pipeline_id>/dependencies/<uuid:dep_id>')
@require_role(['admin', 'editor'])
def remove_dependency(pipeline_id, dep_id):
    pipeline = db.session.get(Pipeline, str(pipeline_id))
    if not pipeline:
        return jsonify({'error': _NOT_FOUND}), 404
    if not can_access_project(pipeline.project_id):
        return jsonify(ACCESS_DENIED), 403
    dep = db.session.query(PipelineDependency).filter_by(
        id=str(dep_id), downstream_id=str(pipeline_id)
    ).first()
    if not dep:
        return jsonify({'error': 'Dependency not found'}), 404
    db.session.delete(dep)
    db.session.commit()
    return jsonify({'deleted': str(dep_id)})


@bp.delete('/pipelines/<uuid:pipeline_id>/webhook-tokens/<uuid:token_id>')
@require_role(['admin', 'editor'])
def revoke_webhook_token(pipeline_id, token_id):
    pipeline = db.session.get(Pipeline, str(pipeline_id))
    if not pipeline:
        return jsonify({'error': _NOT_FOUND}), 404
    if not can_access_project(pipeline.project_id):
        return jsonify(ACCESS_DENIED), 403
    wt = db.session.query(WebhookToken).filter_by(
        id=str(token_id), pipeline_id=str(pipeline_id)
    ).first()
    if not wt:
        return jsonify({'error': 'Token not found'}), 404
    db.session.delete(wt)
    db.session.commit()
    return jsonify({'deleted': str(token_id)})
