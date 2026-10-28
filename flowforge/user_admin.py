"""Create and delete users from the CLI without a password ever being typed into a config
file, stored in plaintext, or passed on a command line (where it would land in shell history
and the process list).

Passwords are either generated here (shown once to the operator) or read from an interactive
prompt by the CLI. Only the bcrypt hash is stored.
"""
import secrets

import bcrypt

from flowforge import audit
from flowforge.db.models import AuditLog, User, db

VALID_ROLES = ('admin', 'editor', 'viewer')
MIN_PASSWORD_LEN = 8


def generate_password() -> str:
    """A random, URL-safe password (24 characters, ~144 bits)."""
    return secrets.token_urlsafe(18)


def create_user(
    username: str,
    role: str = 'editor',
    email: str | None = None,
    password: str | None = None,
    must_change_password: bool = True,
) -> tuple[User, str]:
    """Create a user and return ``(user, password)``. Generates a password when none is given.

    Must be called inside a Flask app context. Raises ValueError for invalid input or a
    duplicate username.
    """
    username = (username or '').strip()
    if not username:
        raise ValueError('username is required')
    if role not in VALID_ROLES:
        raise ValueError(f'role must be one of {list(VALID_ROLES)}')
    if db.session.query(User).filter_by(username=username).first():
        raise ValueError(f'user {username!r} already exists')
    if password is None:
        password = generate_password()
    if len(password) < MIN_PASSWORD_LEN:
        raise ValueError(f'password must be at least {MIN_PASSWORD_LEN} characters')

    user = User(
        username=username,
        password_hash=bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
        role=role,
        email=(email or '').strip().lower() or None,
        must_change_password=must_change_password,
    )
    db.session.add(user)
    db.session.flush()
    if role != 'admin':
        from flowforge.api.routes.users import _add_default_project_membership
        _add_default_project_membership(user.id)
    db.session.commit()
    audit.log_user_change('CREATED', username, user.id)
    return user, password


def delete_user(username: str, purge: bool = False) -> bool:
    """Delete a user by name; ``purge`` also anonymizes their audit-log entries (GDPR).

    Returns False when no such user exists.
    """
    user = db.session.query(User).filter_by(username=username).first()
    if not user:
        return False
    uid = user.id
    if purge:
        anon_name = f'[deleted:{uid[:8]}]'
        (db.session.query(AuditLog)
         .filter((AuditLog.user_id == uid) | (AuditLog.username == username))
         .update({'username': anon_name, 'user_id': None, 'ip_address': None},
                 synchronize_session=False))
    db.session.delete(user)
    db.session.commit()
    audit.log_user_change('DELETED', username, uid)
    return True
