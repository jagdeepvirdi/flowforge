from flask import Blueprint, jsonify, request

from flowforge.api.auth import require_auth
from flowforge.db.models import Pipeline, PipelineVariable, db

bp = Blueprint('pipelines', __name__)


def _pipeline_dict(p: Pipeline) -> dict:
    return {
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'schedule': p.schedule,
        'enabled': p.enabled,
        'timeout_minutes': p.timeout_minutes,
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
    pipelines = db.session.query(Pipeline).order_by(Pipeline.name).all()
    return jsonify([_pipeline_dict(p) for p in pipelines])


@bp.post('/pipelines')
@require_auth
def create_pipeline():
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': 'name is required'}), 400

    pipeline = Pipeline(
        name=data['name'],
        description=data.get('description', ''),
        schedule=data.get('schedule'),
        enabled=data.get('enabled', True),
        timeout_minutes=data.get('timeout_minutes', 60),
    )
    db.session.add(pipeline)
    db.session.flush()

    for var in data.get('variables', []):
        db.session.add(PipelineVariable(
            pipeline_id=pipeline.id,
            var_key=var['var_key'],
            var_value=var['var_value'],
            is_secret=var.get('is_secret', False),
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
    for field in ('name', 'description', 'schedule', 'enabled', 'timeout_minutes'):
        if field in data:
            setattr(pipeline, field, data[field])

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


@bp.post('/pipelines/<uuid:pipeline_id>/run')
@require_auth
def trigger_run(pipeline_id):
    from flowforge.engine.loader import load_pipeline
    from flowforge.engine.runner import run_pipeline

    pipeline = db.session.get(Pipeline, str(pipeline_id))
    if not pipeline:
        return jsonify({'error': 'Pipeline not found'}), 404
    if not pipeline.enabled:
        return jsonify({'error': 'Pipeline is disabled'}), 400

    steps, pipeline_vars = load_pipeline(str(pipeline_id))
    result = run_pipeline(
        pipeline_name=pipeline.name,
        steps=steps,
        pipeline_vars=pipeline_vars,
        triggered_by='web_ui',
        pipeline_id=str(pipeline_id),
    )
    return jsonify({
        'success': result.success,
        'pipeline_name': result.pipeline_name,
        'steps_run': result.steps_run,
        'steps_failed': result.steps_failed,
        'error': result.error,
        'run_id': result.run_id,
    }), 200 if result.success else 500


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
