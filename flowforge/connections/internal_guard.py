"""Refuse database connections that point at FlowForge's own database.

Why: users with the ``editor`` role can run arbitrary SQL through any connection
(``db_query``, ``db_procedure``, report SQL). A connection to FlowForge's own database
whose role has write access lets them read credentials-adjacent tables and alter or delete
audit-log rows (see docs/security.md, "Audit log integrity"). Nothing legitimate in a
normal deployment needs to run user pipelines against the metadata database.

This is defence in depth, **not** a complete control. It compares host, port and database
name, so it cannot see through a proxy/pooler on another port, a different DNS name that
resolves elsewhere, or a second database that mirrors the metadata. The real control is a
least-privilege database role for every connection. Set
``FLOWFORGE_ALLOW_INTERNAL_DB_CONNECTIONS=true`` to opt out (for example to monitor
FlowForge's own database with ``db_health_check``); the choice is then yours and the
audit-log caveats apply.
"""
from __future__ import annotations

import os
import socket

ALLOW_ENV = 'FLOWFORGE_ALLOW_INTERNAL_DB_CONNECTIONS'
_LOCAL_NAMES = {'', 'localhost', '127.0.0.1', '::1', '[::1]'}
_LOOPBACK_IPS = {'127.0.0.1', '::1'}


class InternalDatabaseConnectionError(ValueError):
    """The connection targets FlowForge's own database and the opt-out is not set."""


def _allowed() -> bool:
    return os.environ.get(ALLOW_ENV, '').strip().lower() in ('1', 'true', 'yes')


def _internal_target() -> tuple[str, int, str] | None:
    """(host, port, database) of FlowForge's own PostgreSQL database, or None if unknown."""
    url = ''
    try:
        from flask import current_app
        url = str(current_app.config.get('SQLALCHEMY_DATABASE_URI') or '')
    except RuntimeError:        # outside an app context
        pass
    url = url or os.environ.get('FLOWFORGE_DB_URL', '')
    if not url:
        return None
    from sqlalchemy.engine import make_url
    try:
        u = make_url(url)
    except Exception:
        return None
    if not u.drivername.startswith('postgres') or not u.database:
        return None
    return (u.host or '', int(u.port or 5432), u.database)


def _addresses(host: str) -> set[str]:
    h = host.strip().lower()
    if h in _LOCAL_NAMES:
        return set(_LOOPBACK_IPS)
    try:
        return {info[4][0] for info in socket.getaddrinfo(h, None)}
    except OSError:
        return set()


def _same_host(a: str, b: str) -> bool:
    if a.strip().lower() == b.strip().lower():
        return True
    return bool(_addresses(a) & _addresses(b))


def targets_internal_db(host: str | None, port: int | str | None, database: str | None) -> bool:
    """True if (host, port, database) is FlowForge's own database."""
    target = _internal_target()
    if target is None:
        return False
    t_host, t_port, t_db = target
    try:
        port = int(port or 5432)
    except (TypeError, ValueError):
        return False
    if (database or '') != t_db or port != t_port:
        return False
    return _same_host(host or '', t_host)


def check_allowed(host: str | None, port: int | str | None, database: str | None) -> None:
    """Raise :class:`InternalDatabaseConnectionError` if this targets FlowForge's own database."""
    if _allowed() or not targets_internal_db(host, port, database):
        return
    raise InternalDatabaseConnectionError(
        "This connection points at FlowForge's own database. Pipeline SQL run through it could "
        'read or modify FlowForge tables, including the audit log, so it is refused. Use a '
        f'separate database or a least-privilege role, or set {ALLOW_ENV}=true to allow it.'
    )


def check_config(db_type: str, cfg: dict) -> None:
    """Save-time check of a connection config dict (same rule as the constructor check)."""
    if db_type != 'postgresql' or not isinstance(cfg, dict):
        return
    check_allowed(cfg.get('host', 'localhost'), cfg.get('port', 5432), cfg.get('database', ''))
