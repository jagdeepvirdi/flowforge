"""SQLAlchemy ORM models for FlowForge internal tables."""
import uuid
from datetime import UTC, datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

# ── constants ──
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


class AuditLog(db.Model):
    __tablename__ = 'ff_audit_log'

    id           = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    timestamp    = Column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)
    action       = Column(String(50), nullable=False, index=True)  # e.g., LOGIN, LOGOUT, PIPELINE_RUN, CONFIG_CREATED
    username     = Column(String(255), nullable=False, index=True) # Usually the doer
    user_id      = Column(UUID(as_uuid=False))                     # Nullable for system actions or legacy
    ip_address   = Column(String(45))                              # IPv6 max len
    details      = Column(JSONB, default=dict, nullable=False)     # e.g. pipeline_id, step_name, etc.

class Project(db.Model):
    __tablename__ = 'ff_projects'

    id          = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name        = Column(String(100), nullable=False)
    description = Column(Text)
    color       = Column(String(20), default='#6366f1')
    is_default  = Column(Boolean, default=False, nullable=False)
    created_at  = Column(DateTime(timezone=True), default=_utcnow)

    pipelines        = relationship('Pipeline',       back_populates='project')
    report_configs   = relationship('ReportConfig',   back_populates='project')
    email_configs    = relationship('EmailConfig',    back_populates='project')
    recipient_groups = relationship('RecipientGroup', back_populates='project')
    members          = relationship('ProjectMember',  back_populates='project', cascade=_CASCADE)


class User(db.Model):
    __tablename__ = 'ff_users'
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'editor', 'viewer')", name='ck_user_role'),
    )

    id               = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    username         = Column(String(100), nullable=False, unique=True)
    password_hash    = Column(String(255), nullable=False)
    role             = Column(String(20), nullable=False, default='editor')
    email            = Column(String(255), index=True)  # optional — for password reset
    # MFA (TOTP) — secret and backup codes stored AES-256 encrypted
    mfa_secret       = Column(Text)
    mfa_enabled      = Column(Boolean, nullable=False, default=False)
    mfa_backup_codes = Column(Text)                    # encrypted JSON list of remaining codes
    # SSO — provider ('google' | 'microsoft' | 'saml') and matched email
    sso_provider     = Column(String(20))
    sso_email        = Column(String(255), index=True)
    created_at       = Column(DateTime(timezone=True), default=_utcnow)

    project_memberships = relationship('ProjectMember', back_populates='user', cascade=_CASCADE)


class ProjectMember(db.Model):
    """Team-scoped project access — non-admin users can only see/edit resources
    in projects they're a member of. Admins bypass this check everywhere
    (see flowforge/api/project_access.py)."""
    __tablename__ = 'ff_project_members'
    __table_args__ = (
        UniqueConstraint('project_id', 'user_id', name='uq_project_member'),
    )

    id         = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey(_FF_PROJECTS_ID, ondelete='CASCADE'), nullable=False, index=True)
    user_id    = Column(UUID(as_uuid=False), ForeignKey('ff_users.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    project = relationship('Project', back_populates='members')
    user    = relationship('User', back_populates='project_memberships')


class RecipientGroup(db.Model):
    __tablename__ = 'ff_recipient_groups'

    id            = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name          = Column(String(100), nullable=False)
    description   = Column(Text)
    addresses     = Column(ARRAY(Text), nullable=False)   # To
    cc_addresses  = Column(ARRAY(Text))
    bcc_addresses = Column(ARRAY(Text))
    project_id    = Column(UUID(as_uuid=False), ForeignKey(_FF_PROJECTS_ID, ondelete=_SET_NULL), nullable=True)
    created_at    = Column(DateTime(timezone=True), default=_utcnow)

    email_configs = relationship('EmailConfig', back_populates='recipient_group')
    project       = relationship('Project', back_populates='recipient_groups')


class EmailProvider(db.Model):
    __tablename__ = 'ff_email_providers'
    __table_args__ = (
        CheckConstraint("provider_type IN ('gmail', 'microsoft365', 'smtp', 'sendgrid', 'ses', 'mailgun')", name='ck_email_provider_type'),
    )

    id            = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name          = Column(String(100), nullable=False)
    provider_type = Column(String(20), nullable=False)
    config        = Column(Text, nullable=False)   # encrypted JSON
    is_default    = Column(Boolean, default=False)
    created_at    = Column(DateTime(timezone=True), default=_utcnow)

    email_configs = relationship('EmailConfig', back_populates='provider')


class DbConnection(db.Model):
    __tablename__ = 'ff_db_connections'
    __table_args__ = (
        CheckConstraint(
            "db_type IN ('postgresql', 'oracle', 'mysql', 'mssql', 'odbc', 'redshift', 'snowflake', 'bigquery')",
            name='ck_db_connection_type',
        ),
    )

    id         = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name       = Column(String(100), nullable=False)
    db_type    = Column(String(20), nullable=False)
    config     = Column(Text, nullable=False)   # encrypted JSON
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    report_configs    = relationship('ReportConfig', back_populates='connection')
    bulk_load_configs = relationship('BulkLoadConfig', back_populates='connection')


class SSHConnection(db.Model):
    __tablename__ = 'ff_ssh_connections'

    id         = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name       = Column(String(100), nullable=False)
    config     = Column(Text, nullable=False)   # encrypted JSON (host, port, username, password, key_path)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class BulkLoadConfig(db.Model):
    __tablename__ = 'ff_bulk_load_configs'

    id                  = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name                = Column(String(255), nullable=False)
    description         = Column(Text)
    connection_id       = Column(UUID(as_uuid=False), ForeignKey('ff_db_connections.id', ondelete=_SET_NULL))
    source_directory    = Column(String(500), nullable=False)
    file_prefix         = Column(String(255))
    file_prefix_exclude = Column(String(255))
    file_type           = Column(String(20), default='csv')
    delimiter           = Column(String(5), default=',')
    header_rows         = Column(Integer, default=1)
    footer_rows         = Column(Integer, default=0)
    target_table        = Column(String(255), nullable=False)
    load_mode           = Column(String(20), default='append')
    column_mapping      = Column(JSONB, default=list)
    use_sqlloader       = Column(Boolean, default=False)
    archive_directory   = Column(String(500))
    on_no_files         = Column(String(20), default='skip')
    created_at          = Column(DateTime(timezone=True), default=_utcnow)
    updated_at          = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    connection = relationship('DbConnection', back_populates='bulk_load_configs')


class ReportConfig(db.Model):
    __tablename__ = 'ff_report_configs'
    __table_args__ = (
        CheckConstraint("format IN ('excel', 'csv', 'pdf', 'json')", name='ck_report_format'),
    )

    id                 = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name               = Column(String(255), nullable=False)
    description        = Column(Text)
    connection_id      = Column(UUID(as_uuid=False), ForeignKey('ff_db_connections.id', ondelete=_SET_NULL))
    query              = Column(Text, nullable=False)
    format             = Column(String(20), nullable=False)
    template_path      = Column(String(500))
    output_filename    = Column(String(500), nullable=False)
    title              = Column(String(255))
    sheet_name         = Column(String(100))
    columns            = Column(ARRAY(Text))
    column_formatting  = Column(JSONB, default=list)  # list of per-column format rules
    project_id         = Column(UUID(as_uuid=False), ForeignKey(_FF_PROJECTS_ID, ondelete=_SET_NULL), nullable=True)
    created_at         = Column(DateTime(timezone=True), default=_utcnow)
    updated_at         = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    connection = relationship('DbConnection', back_populates='report_configs')
    project    = relationship('Project', back_populates='report_configs')


class EmailConfig(db.Model):
    __tablename__ = 'ff_email_configs'

    id                  = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name                = Column(String(255), nullable=False)
    description         = Column(Text)
    provider_id         = Column(UUID(as_uuid=False), ForeignKey('ff_email_providers.id', ondelete=_SET_NULL))
    from_name           = Column(String(255))
    subject             = Column(String(500), nullable=False)
    header_text         = Column(String(500))
    body_template       = Column(Text, nullable=False)
    body_format         = Column(String(10), nullable=False, default='html')
    recipient_group_id  = Column(UUID(as_uuid=False), ForeignKey('ff_recipient_groups.id', ondelete=_SET_NULL))
    to_addresses        = Column(ARRAY(Text))
    cc_addresses        = Column(ARRAY(Text))
    bcc_addresses       = Column(ARRAY(Text))
    attachment_max_mb   = Column(Integer, default=10)
    drive_folder_id     = Column(String(255))
    drive_share_message = Column(Text)
    onedrive_folder_id  = Column(String(255))
    project_id          = Column(UUID(as_uuid=False), ForeignKey(_FF_PROJECTS_ID, ondelete=_SET_NULL), nullable=True)
    created_at          = Column(DateTime(timezone=True), default=_utcnow)
    updated_at          = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    provider         = relationship('EmailProvider',    back_populates='email_configs')
    recipient_group  = relationship('RecipientGroup',  back_populates='email_configs')
    project          = relationship('Project',         back_populates='email_configs')


class Pipeline(db.Model):
    __tablename__ = 'ff_pipelines'

    id                      = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name                    = Column(String(255), nullable=False, unique=True)
    description             = Column(Text)
    schedule                = Column(String(100))
    enabled                 = Column(Boolean, default=True)
    timeout_minutes         = Column(Integer, default=60)
    on_failure_webhook_url  = Column(String(500))
    send_only_on_failure    = Column(Boolean, default=False)
    project_id              = Column(UUID(as_uuid=False), ForeignKey(_FF_PROJECTS_ID, ondelete=_SET_NULL), nullable=True)
    created_at              = Column(DateTime(timezone=True), default=_utcnow)
    updated_at              = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    steps          = relationship('PipelineStep', back_populates='pipeline',
                                  order_by='PipelineStep.step_order', cascade=_CASCADE)
    variables      = relationship('PipelineVariable', back_populates='pipeline',
                                  cascade=_CASCADE)
    runs           = relationship('PipelineRun', back_populates='pipeline')
    webhook_tokens = relationship('WebhookToken', back_populates='pipeline',
                                  cascade=_CASCADE)
    project        = relationship('Project', back_populates='pipelines')
    upstream_deps  = relationship('PipelineDependency',
                                  foreign_keys='PipelineDependency.downstream_id',
                                  back_populates='downstream', cascade=_CASCADE)
    downstream_deps = relationship('PipelineDependency',
                                   foreign_keys='PipelineDependency.upstream_id',
                                   back_populates='upstream', cascade=_CASCADE)


class PipelineStep(db.Model):
    __tablename__ = 'ff_pipeline_steps'
    __table_args__ = (
        # Format check only (not an enum) — plugin step types loaded from FLOWFORGE_PLUGIN_DIR
        # are not known when this constraint is defined. The set of *valid, registered* step
        # types is enforced at the application layer via flowforge.engine.loader.get_step_types().
        CheckConstraint(
            "step_type ~ '^[a-z][a-z0-9_]{1,48}$'",
            name='ck_step_type',
        ),
        CheckConstraint("on_error IN ('stop', 'continue')", name='ck_on_error'),
        UniqueConstraint('pipeline_id', 'step_order', name='uq_pipeline_step_order'),
    )

    id             = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    pipeline_id    = Column(UUID(as_uuid=False), ForeignKey(_FF_PIPELINES_ID, ondelete='CASCADE'), nullable=False)
    step_order     = Column(Integer, nullable=False)
    name           = Column(String(255), nullable=False)
    step_type      = Column(String(50), nullable=False)
    config         = Column(JSONB, nullable=False, default=dict)
    on_error       = Column(String(20), default='stop')
    enabled        = Column(Boolean, default=True)
    parallel_group = Column(String(100))  # non-null steps with same value run concurrently

    pipeline = relationship('Pipeline', back_populates='steps')
    upstream_step_deps   = relationship('StepDependency',
                                        foreign_keys='StepDependency.downstream_step_id',
                                        back_populates='downstream_step', cascade=_CASCADE)
    downstream_step_deps = relationship('StepDependency',
                                        foreign_keys='StepDependency.upstream_step_id',
                                        back_populates='upstream_step', cascade=_CASCADE)



class PipelineVariable(db.Model):
    __tablename__ = 'ff_pipeline_variables'
    __table_args__ = (
        UniqueConstraint('pipeline_id', 'var_key', name='uq_pipeline_var_key'),
    )

    id          = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    pipeline_id = Column(UUID(as_uuid=False), ForeignKey(_FF_PIPELINES_ID, ondelete='CASCADE'), nullable=False)
    var_key     = Column(String(100), nullable=False)
    var_value   = Column(Text, nullable=False)
    is_secret   = Column(Boolean, default=False)

    pipeline = relationship('Pipeline', back_populates='variables')


class PipelineDependency(db.Model):
    """Downstream pipeline B runs automatically when all its upstream pipelines succeed."""
    __tablename__ = 'ff_pipeline_dependencies'
    __table_args__ = (
        UniqueConstraint('upstream_id', 'downstream_id', name='uq_pipeline_dependency'),
        CheckConstraint('upstream_id != downstream_id', name='ck_no_self_dependency'),
    )

    id            = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    upstream_id   = Column(UUID(as_uuid=False), ForeignKey(_FF_PIPELINES_ID, ondelete='CASCADE'), nullable=False, index=True)
    downstream_id = Column(UUID(as_uuid=False), ForeignKey(_FF_PIPELINES_ID, ondelete='CASCADE'), nullable=False, index=True)
    created_at    = Column(DateTime(timezone=True), default=_utcnow)

    upstream   = relationship('Pipeline', foreign_keys=[upstream_id],   back_populates='downstream_deps')
    downstream = relationship('Pipeline', foreign_keys=[downstream_id], back_populates='upstream_deps')


class StepDependency(db.Model):
    """Step-level edge within a single pipeline: downstream_step runs after upstream_step.

    `pipeline_id` is deliberately denormalized onto the edge row (not derived via join) so
    `exists_for_pipeline` is a single indexed lookup and the API route can enforce "both steps
    belong to this pipeline" by direct column comparison — Postgres can't declaratively express
    "these two FK targets share a third column's value" without a trigger, so that check is
    enforced at the route layer, not a DB constraint.
    """
    __tablename__ = 'ff_step_dependencies'
    __table_args__ = (
        UniqueConstraint('upstream_step_id', 'downstream_step_id', name='uq_step_dependency'),
        CheckConstraint('upstream_step_id != downstream_step_id', name='ck_no_self_step_dependency'),
    )

    id                 = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    pipeline_id        = Column(UUID(as_uuid=False), ForeignKey(_FF_PIPELINES_ID, ondelete='CASCADE'), nullable=False, index=True)
    upstream_step_id   = Column(UUID(as_uuid=False), ForeignKey('ff_pipeline_steps.id', ondelete='CASCADE'), nullable=False, index=True)
    downstream_step_id = Column(UUID(as_uuid=False), ForeignKey('ff_pipeline_steps.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at         = Column(DateTime(timezone=True), default=_utcnow)

    upstream_step   = relationship('PipelineStep', foreign_keys=[upstream_step_id],   back_populates='downstream_step_deps')
    downstream_step = relationship('PipelineStep', foreign_keys=[downstream_step_id], back_populates='upstream_step_deps')

    @classmethod
    def exists_for_pipeline(cls, pipeline_id: str) -> bool:
        """The single signal the runner's dual-path engine selection branches on."""
        return db.session.query(cls.id).filter_by(pipeline_id=pipeline_id).first() is not None


class PipelineRun(db.Model):
    __tablename__ = 'ff_pipeline_runs'
    __table_args__ = (
        CheckConstraint("status IN ('running','success','failed','cancelled')", name='ck_run_status'),
    )

    id            = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    pipeline_id   = Column(UUID(as_uuid=False), ForeignKey(_FF_PIPELINES_ID, ondelete=_SET_NULL))
    pipeline_name = Column(String(255), nullable=False)
    status        = Column(String(20), nullable=False)
    started_at    = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    finished_at   = Column(DateTime(timezone=True))
    duration_ms   = Column(Integer)
    triggered_by  = Column(String(50))
    error_step    = Column(String(255))
    error_message = Column(Text)

    pipeline  = relationship('Pipeline', back_populates='runs')
    step_runs = relationship('StepRun', back_populates='pipeline_run', cascade=_CASCADE)


class WebhookToken(db.Model):
    """Per-pipeline API tokens for external webhook triggers."""
    __tablename__ = 'ff_webhook_tokens'

    id          = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    pipeline_id = Column(UUID(as_uuid=False), ForeignKey(_FF_PIPELINES_ID, ondelete='CASCADE'), nullable=False)
    label       = Column(String(100), nullable=False, default='')
    token_hash  = Column(String(64), nullable=False, unique=True)  # SHA-256(raw_token)
    enabled     = Column(Boolean, nullable=False, default=True)
    last_used_at = Column(DateTime(timezone=True))
    created_at  = Column(DateTime(timezone=True), default=_utcnow)

    pipeline = relationship('Pipeline', back_populates='webhook_tokens')


class TokenBlocklist(db.Model):
    """Revoked JWT IDs. Entries older than their expires_at are dead weight and can be pruned."""
    __tablename__ = 'ff_token_blocklist'

    jti        = Column(String(36), primary_key=True)
    revoked_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)


class PasswordResetToken(db.Model):
    """Single-use password reset tokens, valid for 1 hour."""
    __tablename__ = 'ff_password_reset_tokens'

    token      = Column(String(64),              primary_key=True)
    user_id    = Column(UUID(as_uuid=False),      ForeignKey('ff_users.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True),  nullable=False, default=_utcnow)
    expires_at = Column(DateTime(timezone=True),  nullable=False)
    used_at    = Column(DateTime(timezone=True))


class SystemSettings(db.Model):
    """Singleton row (id=1) of instance-wide operational settings that override
    the env-var defaults when set. NULL columns mean 'use the env var default'."""
    __tablename__ = 'ff_system_settings'

    id                    = Column(Integer, primary_key=True)
    run_retention_days    = Column(Integer)
    audit_retention_days  = Column(Integer)
    output_ttl_days       = Column(Integer)
    updated_at            = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)
    updated_by            = Column(String(255))


class StepRun(db.Model):
    __tablename__ = 'ff_step_runs'
    __table_args__ = (
        CheckConstraint("status IN ('running','success','failed','skipped')", name='ck_step_run_status'),
    )

    id              = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    pipeline_run_id = Column(UUID(as_uuid=False), ForeignKey('ff_pipeline_runs.id', ondelete='CASCADE'), nullable=False)
    step_name       = Column(String(255), nullable=False)
    step_type       = Column(String(50), nullable=False)
    step_order      = Column(Integer, nullable=False)
    status          = Column(String(20), nullable=False)
    started_at      = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    finished_at     = Column(DateTime(timezone=True))
    duration_ms     = Column(Integer)
    rows_affected   = Column(Integer)
    output_path     = Column(String(500))
    drive_url       = Column(String(500))
    email_sent_to   = Column(ARRAY(Text))
    logs            = Column(Text)
    error_message   = Column(Text)

    pipeline_run = relationship('PipelineRun', back_populates='step_runs')
