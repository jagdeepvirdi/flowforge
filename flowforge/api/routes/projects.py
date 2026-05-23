from flask import Blueprint, jsonify, request

from flowforge.api.auth import require_auth
from flowforge.db.models import (
    DEFAULT_PROJECT_ID, EmailConfig, Pipeline, Project, RecipientGroup,
    ReportConfig, db,
)

bp = Blueprint('projects', __name__)


def _project_dict(p: Project) -> dict:
    return {
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'color': p.color,
        'is_default': p.is_default,
        'created_at': p.created_at.isoformat() if p.created_at else None,
    }


def _resource_counts(project_id: str) -> dict:
    return {
        'pipelines':  db.session.query(Pipeline).filter_by(project_id=project_id).count(),
        'reports':    db.session.query(ReportConfig).filter_by(project_id=project_id).count(),
        'emails':     db.session.query(EmailConfig).filter_by(project_id=project_id).count(),
        'recipients': db.session.query(RecipientGroup).filter_by(project_id=project_id).count(),
    }


@bp.get('/projects')
@require_auth
def list_projects():
    projects = (
        db.session.query(Project)
        .order_by(Project.is_default.desc(), Project.name)
        .all()
    )
    result = []
    for p in projects:
        d = _project_dict(p)
        d['resource_counts'] = _resource_counts(p.id)
        result.append(d)
    return jsonify(result)


@bp.post('/projects')
@require_auth
def create_project():
    data = request.get_json() or {}
    if not data.get('name'):
        return jsonify({'error': 'name is required'}), 400

    project = Project(
        name=data['name'],
        description=data.get('description', ''),
        color=data.get('color', '#6366f1'),
        is_default=False,
    )
    db.session.add(project)
    db.session.commit()
    return jsonify(_project_dict(project)), 201


@bp.get('/projects/<uuid:project_id>')
@require_auth
def get_project(project_id):
    project = db.session.get(Project, str(project_id))
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    result = _project_dict(project)
    result['resource_counts'] = _resource_counts(str(project_id))
    return jsonify(result)


@bp.patch('/projects/<uuid:project_id>')
@require_auth
def update_project(project_id):
    project = db.session.get(Project, str(project_id))
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    data = request.get_json() or {}
    for field in ('name', 'description', 'color'):
        if field in data:
            setattr(project, field, data[field])

    db.session.commit()
    return jsonify(_project_dict(project))


@bp.delete('/projects/<uuid:project_id>')
@require_auth
def delete_project(project_id):
    project = db.session.get(Project, str(project_id))
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    if project.is_default:
        return jsonify({'error': 'The Default project cannot be deleted'}), 400

    counts = _resource_counts(str(project_id))
    total = sum(counts.values())
    if total > 0:
        return jsonify({
            'error': (
                'Project has resources and cannot be deleted. '
                'Move or delete its pipelines, reports, email configs, '
                'and recipient groups first.'
            ),
            'resource_counts': counts,
        }), 409

    db.session.delete(project)
    db.session.commit()
    return jsonify({'deleted': str(project_id)})
