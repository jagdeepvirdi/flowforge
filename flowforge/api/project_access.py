"""Project-membership access control — shared by pipelines/reports/emails/
recipients/projects routes.

Non-admin users may only see/modify resources whose project_id is one they
are a member of (ff_project_members). Admins bypass this check everywhere,
matching the existing require_role() convention (models.py: 'admin' can
do everything).
"""
from flask import g

from flowforge.db.models import ProjectMember, db

ACCESS_DENIED = {'error': 'Access denied to this project'}


def is_admin() -> bool:
    return g.user_token.get('role') == 'admin'


def accessible_project_ids() -> list[str] | None:
    """Return the project IDs the current user may access, or None if the
    caller is an admin (i.e. unrestricted — callers should skip filtering)."""
    if is_admin():
        return None
    user_id = g.current_user_id
    if not user_id:
        return []
    rows = db.session.query(ProjectMember.project_id).filter_by(user_id=user_id).all()
    return [r[0] for r in rows]


def can_access_project(project_id: str | None) -> bool:
    """Whether the current user may see/modify a resource in this project."""
    if is_admin():
        return True
    if not project_id:
        return False
    user_id = g.current_user_id
    if not user_id:
        return False
    return db.session.query(ProjectMember).filter_by(
        project_id=project_id, user_id=user_id,
    ).first() is not None


def scope_query(query, project_id_column):
    """Restrict a query to the current user's accessible projects (no-op for admins)."""
    ids = accessible_project_ids()
    if ids is None:
        return query
    return query.filter(project_id_column.in_(ids))
