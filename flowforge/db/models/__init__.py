"""SQLAlchemy ORM models for FlowForge internal tables.

Split into domain modules (auth, audit, projects, connections, email, reports,
bulk_load, pipelines, settings) purely for navigability — every symbol that
used to live directly in this file (when it was a single models.py) is
re-exported here unchanged, so `from flowforge.db.models import X` keeps
working exactly as before for all existing call sites. See _shared.py for why
splitting the classes across files doesn't introduce circular imports between
them (relationships/foreign keys are declared as strings, resolved by
SQLAlchemy's own registry rather than by Python import order) — but every
domain module below must still be imported here at least once, so its classes
actually register with `db` before anything queries the ORM.
"""
from flowforge.db.models._shared import DEFAULT_PROJECT_ID, db
from flowforge.db.models.audit import AuditLog
from flowforge.db.models.auth import PasswordResetToken, ProjectMember, TokenBlocklist, User
from flowforge.db.models.bulk_load import BulkLoadConfig
from flowforge.db.models.connections import DbConnection, SSHConnection
from flowforge.db.models.email import EmailConfig, EmailProvider, RecipientGroup
from flowforge.db.models.pipelines import (
    Pipeline,
    PipelineDependency,
    PipelineRun,
    PipelineStep,
    PipelineVariable,
    StepDependency,
    StepRun,
    WebhookToken,
)
from flowforge.db.models.projects import Project
from flowforge.db.models.reports import ReportConfig
from flowforge.db.models.settings import SystemSettings

__all__ = [
    'db',
    'DEFAULT_PROJECT_ID',
    'AuditLog',
    'BulkLoadConfig',
    'DbConnection',
    'EmailConfig',
    'EmailProvider',
    'PasswordResetToken',
    'Pipeline',
    'PipelineDependency',
    'PipelineRun',
    'PipelineStep',
    'PipelineVariable',
    'Project',
    'ProjectMember',
    'RecipientGroup',
    'ReportConfig',
    'SSHConnection',
    'StepDependency',
    'StepRun',
    'SystemSettings',
    'TokenBlocklist',
    'User',
    'WebhookToken',
]
