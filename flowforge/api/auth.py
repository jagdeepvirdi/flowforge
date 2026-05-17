"""JWT authentication — single-user v1."""
import os
from datetime import datetime, timedelta, timezone
from functools import wraps

import bcrypt
import jwt
from flask import current_app, jsonify, request

from flowforge.db.models import User, db


def _algorithm() -> str:
    return current_app.config.get('JWT_ALGORITHM', 'HS256')


def _secret() -> str:
    return current_app.config['SECRET_KEY']


def _expiry_hours() -> int:
    return current_app.config.get('JWT_EXPIRY_HOURS', 24)


def generate_token(username: str) -> str:
    payload = {
        'sub': username,
        'iat': datetime.now(timezone.utc),
        'exp': datetime.now(timezone.utc) + timedelta(hours=_expiry_hours()),
    }
    return jwt.encode(payload, _secret(), algorithm=_algorithm())


def verify_token(token: str) -> str | None:
    """Return the username if the token is valid, else None."""
    try:
        payload = jwt.decode(token, _secret(), algorithms=[_algorithm()])
        return payload['sub']
    except jwt.PyJWTError:
        return None


def login(username: str, password: str) -> str | None:
    """Return a JWT if credentials are correct, else None."""
    user = db.session.query(User).filter_by(username=username).first()
    if not user:
        return None
    if not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        return None
    return generate_token(username)


def require_auth(f):
    """Decorator: require a valid Bearer JWT in the Authorization header."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        header = request.headers.get('Authorization', '')
        if not header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid Authorization header'}), 401
        token = header[len('Bearer '):]
        if not verify_token(token):
            return jsonify({'error': 'Invalid or expired token'}), 401
        return f(*args, **kwargs)
    return wrapper
