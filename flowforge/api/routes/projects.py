from flask import Blueprint, g, jsonify, request

import flowforge.audit as audit
from flowforge.api.auth import require_auth, require_role
from flowforge.api.project_access import (
    ACCESS_DENIED,
    accessible_project_ids,
    can_access_project,
    is_admin,
)
from flowforge.db.models import (
    EmailConfig,
    Pipeline,
    Project,
    ProjectMember,
    RecipientGroup,
    ReportConfig,
    User,
    db,
)

bp = Blueprint('projects', __name__)

# ── constants ──
_NOT_FOUND = 'Project not found'


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
    query = db.session.query(Project).order_by(Project.is_default.desc(), Project.name)
    ids = accessible_project_ids()
    if ids is not None:
        query = query.filter(Project.id.in_(ids))
    result = []
    for p in query.all():
        d = _project_dict(p)
        d['resource_counts'] = _resource_counts(p.id)
        result.append(d)
    return jsonify(result)


@bp.post('/projects')
@require_role(['admin', 'editor'])
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
    db.session.flush()

    # The creator must be able to see/use the project they just created —
    # admins don't need a membership row (they bypass the check everywhere).
    if not is_admin() and g.current_user_id:
        db.session.add(ProjectMember(project_id=project.id, user_id=g.current_user_id))

    db.session.commit()
    return jsonify(_project_dict(project)), 201


@bp.get('/projects/<uuid:project_id>')
@require_auth
def get_project(project_id):
    project = db.session.get(Project, str(project_id))
    if not project:
        return jsonify({'error': _NOT_FOUND}), 404
    if not can_access_project(project.id):
        return jsonify(ACCESS_DENIED), 403
    result = _project_dict(project)
    result['resource_counts'] = _resource_counts(str(project_id))
    return jsonify(result)


@bp.patch('/projects/<uuid:project_id>')
@require_role(['admin', 'editor'])
def update_project(project_id):
    project = db.session.get(Project, str(project_id))
    if not project:
        return jsonify({'error': _NOT_FOUND}), 404
    if not can_access_project(project.id):
        return jsonify(ACCESS_DENIED), 403

    data = request.get_json() or {}
    for field in ('name', 'description', 'color'):
        if field in data:
            setattr(project, field, data[field])

    db.session.commit()
    audit.log_project_change('UPDATED', project.name, project.id)
    return jsonify(_project_dict(project))


@bp.delete('/projects/<uuid:project_id>')
@require_role(['admin', 'editor'])
def delete_project(project_id):
    project = db.session.get(Project, str(project_id))
    if not project:
        return jsonify({'error': _NOT_FOUND}), 404
    if not can_access_project(project.id):
        return jsonify(ACCESS_DENIED), 403
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


# ── Project members (team-scoped access) ──────────────────────────────────────

def _member_dict(m: ProjectMember) -> dict:
    return {
        'id': m.id,
        'user_id': m.user_id,
        'username': m.user.username if m.user else None,
        'role': m.user.role if m.user else None,
        'created_at': m.created_at.isoformat() if m.created_at else None,
    }


@bp.get('/projects/<uuid:project_id>/members')
@require_auth
def list_project_members(project_id):
    project = db.session.get(Project, str(project_id))
    if not project:
        return jsonify({'error': _NOT_FOUND}), 404
    if not can_access_project(project.id):
        return jsonify(ACCESS_DENIED), 403
    members = (
        db.session.query(ProjectMember)
        .filter_by(project_id=str(project_id))
        .join(User)
        .order_by(User.username)
        .all()
    )
    return jsonify([_member_dict(m) for m in members])


@bp.post('/projects/<uuid:project_id>/members')
@require_role('admin')
def add_project_member(project_id):
    project = db.session.get(Project, str(project_id))
    if not project:
        return jsonify({'error': _NOT_FOUND}), 404

    data = request.get_json() or {}
    user_id = str(data.get('user_id', '')).strip()
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    existing = db.session.query(ProjectMember).filter_by(
        project_id=str(project_id), user_id=user_id,
    ).first()
    if existing:
        return jsonify({'error': 'User is already a member of this project'}), 409

    member = ProjectMember(project_id=str(project_id), user_id=user_id)
    db.session.add(member)
    db.session.commit()
    audit.log_project_change('MEMBER_ADDED', project.name, project.id)
    return jsonify(_member_dict(member)), 201


@bp.delete('/projects/<uuid:project_id>/members/<uuid:user_id>')
@require_role('admin')
def remove_project_member(project_id, user_id):
    project = db.session.get(Project, str(project_id))
    if not project:
        return jsonify({'error': _NOT_FOUND}), 404
    member = db.session.query(ProjectMember).filter_by(
        project_id=str(project_id), user_id=str(user_id),
    ).first()
    if not member:
        return jsonify({'error': 'Membership not found'}), 404
    db.session.delete(member)
    db.session.commit()
    audit.log_project_change('MEMBER_REMOVED', project.name, project.id)
    return jsonify({'deleted': str(user_id)})
