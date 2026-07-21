from flask import Blueprint, jsonify, request

from flowforge.api.auth import require_auth, require_role
from flowforge.api.project_access import ACCESS_DENIED, can_access_project
from flowforge.db.models import Pipeline, PipelineStep, StepDependency, db
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
    if not can_access_project(pipeline.project_id):
        return jsonify(ACCESS_DENIED), 403
    return jsonify([_step_dict(s) for s in pipeline.steps])


@bp.post('/pipelines/<uuid:pipeline_id>/steps')
@require_auth
def add_step(pipeline_id):
    pipeline = db.session.get(Pipeline, str(pipeline_id))
    if not pipeline:
        return jsonify({'error': 'Pipeline not found'}), 404
    if not can_access_project(pipeline.project_id):
        return jsonify(ACCESS_DENIED), 403

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
    pipeline = db.session.get(Pipeline, step.pipeline_id)
    if pipeline and not can_access_project(pipeline.project_id):
        return jsonify(ACCESS_DENIED), 403

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
    pipeline = db.session.get(Pipeline, step.pipeline_id)
    if pipeline and not can_access_project(pipeline.project_id):
        return jsonify(ACCESS_DENIED), 403
    db.session.delete(step)
    db.session.commit()
    return jsonify({'deleted': str(step_id)})


# ── Step Dependencies (Phase 14 Option B, Milestone 1) ───────────────────────
# Additive only — the runner still executes purely off step_order/parallel_group. These edges
# have no effect on execution until the Milestone 2 DAG engine lands.

def _creates_step_cycle(pipeline_id: str, new_upstream_id: str, new_downstream_id: str) -> bool:
    """Return True if adding upstream→downstream would close a cycle in this pipeline's step graph.

    Loads the whole per-pipeline edge set in one query into an in-memory adjacency dict, then
    does a visited-set/stack traversal — unlike routes/pipelines.py's `_has_path` (bound to
    PipelineDependency, one query per hop), this stays safe to call on every request, including
    a future canvas keystroke in Milestone 3.
    """
    edges = db.session.query(StepDependency).filter_by(pipeline_id=pipeline_id).all()
    adjacency: dict[str, list[str]] = {}
    for e in edges:
        adjacency.setdefault(e.upstream_step_id, []).append(e.downstream_step_id)

    # The new edge closes a cycle iff new_upstream_id is already reachable from
    # new_downstream_id (downstream can already get back around to upstream).
    visited: set[str] = set()
    stack = [new_downstream_id]
    while stack:
        current = stack.pop()
        if current == new_upstream_id:
            return True
        if current in visited:
            continue
        visited.add(current)
        stack.extend(adjacency.get(current, []))
    return False


def _step_dep_dict(d: StepDependency) -> dict:
    return {
        'dep_id':             d.id,
        'upstream_step_id':   d.upstream_step_id,
        'downstream_step_id': d.downstream_step_id,
    }


@bp.get('/pipelines/<uuid:pipeline_id>/step-dependencies')
@require_auth
def list_step_dependencies(pipeline_id):
    pipeline = db.session.get(Pipeline, str(pipeline_id))
    if not pipeline:
        return jsonify({'error': 'Pipeline not found'}), 404
    if not can_access_project(pipeline.project_id):
        return jsonify(ACCESS_DENIED), 403
    deps = db.session.query(StepDependency).filter_by(pipeline_id=str(pipeline_id)).all()
    return jsonify([_step_dep_dict(d) for d in deps])


@bp.post('/pipelines/<uuid:pipeline_id>/step-dependencies')
@require_role(['admin', 'editor'])
def add_step_dependency(pipeline_id):
    pipeline_id = str(pipeline_id)
    pipeline = db.session.get(Pipeline, pipeline_id)
    if not pipeline:
        return jsonify({'error': 'Pipeline not found'}), 404
    if not can_access_project(pipeline.project_id):
        return jsonify(ACCESS_DENIED), 403

    data = request.get_json(silent=True) or {}
    upstream_step_id = str(data.get('upstream_step_id', '')).strip()
    downstream_step_id = str(data.get('downstream_step_id', '')).strip()
    if not upstream_step_id or not downstream_step_id:
        return jsonify({'error': 'upstream_step_id and downstream_step_id are required'}), 400
    if upstream_step_id == downstream_step_id:
        return jsonify({'error': 'A step cannot depend on itself'}), 400

    upstream_step = db.session.get(PipelineStep, upstream_step_id)
    if not upstream_step or upstream_step.pipeline_id != pipeline_id:
        return jsonify({'error': 'upstream_step_id not found in this pipeline'}), 404
    downstream_step = db.session.get(PipelineStep, downstream_step_id)
    if not downstream_step or downstream_step.pipeline_id != pipeline_id:
        return jsonify({'error': 'downstream_step_id not found in this pipeline'}), 404

    if _creates_step_cycle(pipeline_id, upstream_step_id, downstream_step_id):
        return jsonify({'error': 'Adding this dependency would create a circular dependency'}), 409

    existing = db.session.query(StepDependency).filter_by(
        upstream_step_id=upstream_step_id, downstream_step_id=downstream_step_id
    ).first()
    if existing:
        return jsonify({'error': 'Dependency already exists'}), 409

    dep = StepDependency(
        pipeline_id=pipeline_id,
        upstream_step_id=upstream_step_id,
        downstream_step_id=downstream_step_id,
    )
    db.session.add(dep)
    db.session.commit()
    return jsonify(_step_dep_dict(dep)), 201


@bp.delete('/pipelines/<uuid:pipeline_id>/step-dependencies/<uuid:dep_id>')
@require_role(['admin', 'editor'])
def remove_step_dependency(pipeline_id, dep_id):
    pipeline = db.session.get(Pipeline, str(pipeline_id))
    if not pipeline:
        return jsonify({'error': 'Pipeline not found'}), 404
    if not can_access_project(pipeline.project_id):
        return jsonify(ACCESS_DENIED), 403
    dep = db.session.query(StepDependency).filter_by(
        id=str(dep_id), pipeline_id=str(pipeline_id)
    ).first()
    if not dep:
        return jsonify({'error': 'Dependency not found'}), 404
    db.session.delete(dep)
    db.session.commit()
    return jsonify({'deleted': str(dep_id)})
