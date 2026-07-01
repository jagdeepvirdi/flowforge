from flask import Blueprint, jsonify, request

from flowforge.api.auth import require_auth
from flowforge.db.models import Pipeline, PipelineStep, db
from flowforge.engine.loader import get_step_types, is_plugin_step_type

bp = Blueprint('steps', __name__)


@bp.get('/step-types')
@require_auth
def list_step_types():
    """All registered step types (built-in + plugins loaded from FLOWFORGE_PLUGIN_DIR)."""
    return jsonify([
        {'type': t, 'plugin': is_plugin_step_type(t)}
        for t in get_step_types()
    ])


def _step_dict(s: PipelineStep) -> dict:
    return {
        'id':             s.id,
        'pipeline_id':    s.pipeline_id,
        'step_order':     s.step_order,
        'name':           s.name,
        'step_type':      s.step_type,
        'config':         s.config,
        'on_error':       s.on_error,
        'enabled':        s.enabled,
        'parallel_group': s.parallel_group,
    }


@bp.get('/pipelines/<uuid:pipeline_id>/steps')
@require_auth
def list_steps(pipeline_id):
    pipeline = db.session.get(Pipeline, str(pipeline_id))
    if not pipeline:
        return jsonify({'error': 'Pipeline not found'}), 404
    return jsonify([_step_dict(s) for s in pipeline.steps])


@bp.post('/pipelines/<uuid:pipeline_id>/steps')
@require_auth
def add_step(pipeline_id):
    pipeline = db.session.get(Pipeline, str(pipeline_id))
    if not pipeline:
        return jsonify({'error': 'Pipeline not found'}), 404

    data = request.get_json() or {}
    valid_types = set(get_step_types())
    if data.get('step_type') not in valid_types:
        return jsonify({'error': f'step_type must be one of: {", ".join(sorted(valid_types))}'}), 400
    if not data.get('name'):
        return jsonify({'error': 'name is required'}), 400

    max_order = max((s.step_order for s in pipeline.steps), default=0)
    step = PipelineStep(
        pipeline_id=str(pipeline_id),
        step_order=data.get('step_order', max_order + 1),
        name=data['name'],
        step_type=data['step_type'],
        config=data.get('config', {}),
        on_error=data.get('on_error', 'stop'),
        enabled=data.get('enabled', True),
        parallel_group=data.get('parallel_group') or None,
    )
    db.session.add(step)
    db.session.commit()
    return jsonify(_step_dict(step)), 201


@bp.put('/pipeline-steps/<uuid:step_id>')
@require_auth
def update_step(step_id):
    step = db.session.get(PipelineStep, str(step_id))
    if not step:
        return jsonify({'error': 'Step not found'}), 404

    data = request.get_json() or {}
    for field in ('name', 'config', 'on_error', 'enabled', 'parallel_group'):
        if field in data:
            setattr(step, field, data[field] or None if field == 'parallel_group' else data[field])
    if 'step_type' in data:
        if data['step_type'] not in set(get_step_types()):
            return jsonify({'error': 'Invalid step_type'}), 400
        step.step_type = data['step_type']

    # Two-phase swap to avoid (pipeline_id, step_order) unique constraint violation.
    # Negative temp is guaranteed safe: real step orders are always positive integers.
    if 'step_order' in data and data['step_order'] != step.step_order:
        new_order = data['step_order']
        old_order = step.step_order
        occupant = (
            db.session.query(PipelineStep)
            .with_for_update()
            .filter_by(pipeline_id=step.pipeline_id, step_order=new_order)
            .filter(PipelineStep.id != step.id)
            .first()
        )
        if occupant:
            occupant.step_order = -old_order  # negative: never collides with a real step order
            db.session.flush()
            step.step_order = new_order
            db.session.flush()
            occupant.step_order = old_order
        else:
            step.step_order = new_order

    db.session.commit()
    return jsonify(_step_dict(step))


@bp.delete('/pipeline-steps/<uuid:step_id>')
@require_auth
def delete_step(step_id):
    step = db.session.get(PipelineStep, str(step_id))
    if not step:
        return jsonify({'error': 'Step not found'}), 404
    db.session.delete(step)
    db.session.commit()
    return jsonify({'deleted': str(step_id)})
