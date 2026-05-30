"""User management API — admin-only CRUD + self-service change-password + GDPR endpoints."""
import bcrypt
from flask import Blueprint, g, jsonify, request

import flowforge.audit as audit
from flowforge.api.auth import require_auth, require_role
from flowforge.db.models import AuditLog, PipelineRun, User, db

bp = Blueprint('users', __name__)

# ── constants ──
_NOT_FOUND = 'User not found'

_VALID_ROLES = {'admin', 'editor', 'viewer'}


def _user_dict(u: User) -> dict:
    return {
        'id': u.id,
        'username': u.username,
        'role': u.role,
        'email': u.email,
        'mfa_enabled': u.mfa_enabled,
        'sso_provider': u.sso_provider,
        'created_at': u.created_at.isoformat() if u.created_at else None,
    }


@bp.get('/users')
@require_role('admin')
def list_users():
    users = db.session.query(User).order_by(User.created_at).all()
    return jsonify([_user_dict(u) for u in users])


@bp.post('/users')
@require_role('admin')
def create_user():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    role = (data.get('role') or 'editor').strip()

    if not username or not password:
        return jsonify({'error': 'username and password are required'}), 400
    if role not in _VALID_ROLES:
        return jsonify({'error': f'role must be one of {sorted(_VALID_ROLES)}'}), 400
    if db.session.query(User).filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 409

    email = (data.get('email') or '').strip().lower() or None
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user = User(username=username, password_hash=pw_hash, role=role, email=email)
    db.session.add(user)
    db.session.commit()
    audit.log_pipeline_change('USER_CREATED', username, user.id)
    return jsonify(_user_dict(user)), 201


@bp.patch('/users/<uuid:user_id>')
@require_role('admin')
def update_user(user_id):
    user = db.session.get(User, str(user_id))
    if not user:
        return jsonify({'error': _NOT_FOUND}), 404

    data = request.get_json(silent=True) or {}
    new_role = data.get('role')
    new_username = (data.get('username') or '').strip() or None

    # Prevent admin from demoting themselves
    if new_role and new_role != user.role:
        if str(user_id) == g.current_user_id and new_role != 'admin':
            return jsonify({'error': 'Cannot demote your own account'}), 403
        if new_role not in _VALID_ROLES:
            return jsonify({'error': f'role must be one of {sorted(_VALID_ROLES)}'}), 400
        user.role = new_role

    if new_username and new_username != user.username:
        if db.session.query(User).filter_by(username=new_username).first():
            return jsonify({'error': 'Username already exists'}), 409
        user.username = new_username

    new_email = data.get('email')
    if new_email is not None:
        user.email = (new_email.strip().lower() or None)

    db.session.commit()
    audit.log_pipeline_change('USER_UPDATED', user.username, user.id)
    return jsonify(_user_dict(user))


@bp.delete('/users/<uuid:user_id>')
@require_role('admin')
def delete_user(user_id):
    if str(user_id) == g.current_user_id:
        return jsonify({'error': 'Cannot delete your own account'}), 403

    user = db.session.get(User, str(user_id))
    if not user:
        return jsonify({'error': _NOT_FOUND}), 404

    username = user.username
    uid      = user.id
    purge    = request.args.get('purge', '').lower() == 'true'

    if purge:
        _gdpr_anonymize(uid, username)

    db.session.delete(user)
    db.session.commit()
    audit.log_pipeline_change('USER_DELETED', username, uid)
    return jsonify({'message': f'User {username!r} deleted', 'purged': purge})


def _gdpr_anonymize(user_id: str, username: str) -> None:
    """Anonymize all personal data in audit log entries for this user."""
    anon_name = f'[deleted:{user_id[:8]}]'
    (db.session.query(AuditLog)
     .filter((AuditLog.user_id == user_id) | (AuditLog.username == username))
     .update({'username': anon_name, 'user_id': None, 'ip_address': None},
             synchronize_session=False))


@bp.get('/users/<uuid:user_id>/export')
@require_role('admin')
def export_user_data(user_id):
    """GDPR data export — returns all personal data stored for a user as JSON."""
    user = db.session.get(User, str(user_id))
    if not user:
        return jsonify({'error': _NOT_FOUND}), 404

    audit_entries = (
        db.session.query(AuditLog)
        .filter((AuditLog.user_id == user.id) | (AuditLog.username == user.username))
        .order_by(AuditLog.timestamp.desc())
        .limit(1000)
        .all()
    )

    pipeline_runs = (
        db.session.query(PipelineRun)
        .filter(PipelineRun.triggered_by == user.username)
        .order_by(PipelineRun.started_at.desc())
        .limit(500)
        .all()
    )

    return jsonify({
        'user': _user_dict(user),
        'audit_log': [
            {
                'id': e.id,
                'timestamp': e.timestamp.isoformat() if e.timestamp else None,
                'action': e.action,
                'ip_address': e.ip_address,
                'details': e.details,
            }
            for e in audit_entries
        ],
        'pipeline_runs': [
            {
                'id': r.id,
                'pipeline_name': r.pipeline_name,
                'status': r.status,
                'started_at': r.started_at.isoformat() if r.started_at else None,
                'triggered_by': r.triggered_by,
            }
            for r in pipeline_runs
        ],
    })


@bp.post('/auth/change-password')
@require_auth
def change_password():
    data = request.get_json(silent=True) or {}
    current_pw = data.get('current_password') or ''
    new_pw = data.get('new_password') or ''

    if not current_pw or not new_pw:
        return jsonify({'error': 'current_password and new_password are required'}), 400
    if len(new_pw) < 8:
        return jsonify({'error': 'new_password must be at least 8 characters'}), 400

    user = db.session.get(User, g.current_user_id)
    if not user:
        return jsonify({'error': _NOT_FOUND}), 404
    if not bcrypt.checkpw(current_pw.encode(), user.password_hash.encode()):
        return jsonify({'error': 'Current password is incorrect'}), 401

    user.password_hash = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
    db.session.commit()
    return jsonify({'message': 'Password changed successfully'})
