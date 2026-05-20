from flask import Blueprint, jsonify, request

from flowforge.api.auth import require_auth
from flowforge.db.models import Pipeline, PipelineStep, db

bp = Blueprint('steps', __name__)

_VALID_TYPES = {'db_procedure', 'db_query', 'report', 'email', 'drive_upload', 'ai_analyze'}


def _step_dict(s: PipelineStep) -> dict:
    return {
        'id': s.id,
        'pipeline_id': s.pipeline_id,
        'step_order': s.step_order,
        'name': s.name,
        'step_type': s.step_type,
        'config': s.config,
        'on_error': s.on_error,
        'enabled': s.enabled,
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
    if data.get('step_type') not in _VALID_TYPES:
        return jsonify({'error': f'step_type must be one of: {", ".join(sorted(_VALID_TYPES))}'}), 400
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
    for field in ('name', 'config', 'on_error', 'enabled'):
        if field in data:
            setattr(step, field, data[field])
    if 'step_type' in data:
        if data['step_type'] not in _VALID_TYPES:
            return jsonify({'error': 'Invalid step_type'}), 400
        step.step_type = data['step_type']

    # DB-1: two-phase swap to avoid (pipeline_id, step_order) unique constraint violation
    if 'step_order' in data and data['step_order'] != step.step_order:
        new_order = data['step_order']
        old_order = step.step_order
        occupant = (
            db.session.query(PipelineStep)
            .filter_by(pipeline_id=step.pipeline_id, step_order=new_order)
            .filter(PipelineStep.id != step.id)
            .first()
        )
        if occupant:
            occupant.step_order = 999999  # vacate the slot
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
