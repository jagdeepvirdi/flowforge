"""Shared SQLAlchemy instance, helpers, and cross-domain constants.

Every domain module in this package imports `db` from here rather than
creating its own SQLAlchemy() instance — there must be exactly one, since
Flask-SQLAlchemy binds it to the app in flowforge/api/app.py's db.init_app(app).

Relationships and foreign keys across domain modules are declared with string
references (e.g. relationship('Pipeline', ...), ForeignKey('ff_users.id')),
which SQLAlchemy resolves against its own mapper/metadata registry at
configure-mappers time — not by Python import order. So domain modules don't
need to import each other, and can be split without introducing circular
imports between them; they only need to all be imported once (see
__init__.py) before anything queries the ORM.
"""
import uuid
from datetime import UTC, datetime

from flask_sqlalchemy import SQLAlchemy

# ── constants shared across domain modules ──
_SET_NULL         = 'SET NULL'
_FF_PROJECTS_ID   = 'ff_projects.id'
_CASCADE          = 'all, delete-orphan'
_FF_PIPELINES_ID  = 'ff_pipelines.id'

db = SQLAlchemy()

DEFAULT_PROJECT_ID = '00000000-0000-0000-0000-000000000001'


def _uuid():
    return str(uuid.uuid4())


def _utcnow():
    return datetime.now(UTC)
