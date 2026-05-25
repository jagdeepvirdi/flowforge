"""JWT authentication — single-user v1."""
import os
import uuid as _uuid_mod
from datetime import datetime, timedelta, timezone
from functools import wraps

import bcrypt
import jwt
from flask import current_app, g, jsonify, request

from flowforge.db.models import TokenBlocklist, User, db


def _algorithm() -> str:
    return current_app.config.get('JWT_ALGORITHM', 'HS256')


def _secret() -> str:
    # SEC-2: use JWT_SECRET (separate from the AES encryption key)
    return current_app.config.get('JWT_SECRET') or current_app.config['SECRET_KEY']


def _expiry_hours() -> int:
    return current_app.config.get('JWT_EXPIRY_HOURS', 24)


def generate_token(user: User) -> str:
    payload = {
        'sub': user.username,
        'uid': user.id,
        'role': user.role,
        'jti': str(_uuid_mod.uuid4()),
        'iat': datetime.now(timezone.utc),
        'exp': datetime.now(timezone.utc) + timedelta(hours=_expiry_hours()),
    }
    return jwt.encode(payload, _secret(), algorithm=_algorithm())


def verify_token(token: str) -> dict | None:
    """Return the payload if the token is valid and not revoked, else None."""
    try:
        payload = jwt.decode(token, _secret(), algorithms=[_algorithm()])
        jti = payload.get('jti')
        if jti and db.session.get(TokenBlocklist, jti) is not None:
            return None
        return payload
    except jwt.PyJWTError:
        return None


def revoke_token(token: str) -> str | None:
    """Add the token's jti to the blocklist. Returns the username on success, None if invalid.

    Tokens issued before jti was added (no jti claim) are not blocklisted — the client
    must still clear its local storage; the token will expire naturally within 24h.
    """
    try:
        payload = jwt.decode(token, _secret(), algorithms=[_algorithm()])
    except jwt.PyJWTError:
        return None
    jti = payload.get('jti')
    exp = payload.get('exp')
    if jti:
        expires_at = datetime.fromtimestamp(exp, tz=timezone.utc) if exp else datetime.now(timezone.utc)
        db.session.merge(TokenBlocklist(jti=jti, expires_at=expires_at))
        db.session.commit()
    return payload.get('sub')


def login(username: str, password: str) -> str | None:
    """Return a JWT if credentials are correct, else None."""
    user = db.session.query(User).filter_by(username=username).first()
    if not user:
        return None
    if not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        return None
    return generate_token(user)


def require_auth(f):
    """Decorator: require a valid Bearer JWT in the Authorization header.
    Stores the user payload in flask.g.user_token.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        header = request.headers.get('Authorization', '')
        if not header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid Authorization header'}), 401
        token = header[len('Bearer '):]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401
        g.user_token = payload
        return f(*args, **kwargs)
    return wrapper


def require_role(roles: str | list[str]):
    """Decorator: require the user to have one of the specified roles."""
    if isinstance(roles, str):
        roles = [roles]

    def decorator(f):
        @wraps(f)
        @require_auth
        def wrapper(*args, **kwargs):
            user_role = g.user_token.get('role', 'viewer')
            if 'admin' == user_role:  # admins can do everything
                return f(*args, **kwargs)
            if user_role not in roles:
                return jsonify({'error': f'Access denied: required role in {roles}'}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator
