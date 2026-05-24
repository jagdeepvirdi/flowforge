"""SQLAlchemy ORM models for FlowForge internal tables."""
import uuid
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, ForeignKey,
    Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

db = SQLAlchemy()

DEFAULT_PROJECT_ID = '00000000-0000-0000-0000-000000000001'


def _uuid():
    return str(uuid.uuid4())


def _utcnow():
    return datetime.now(timezone.utc)


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


class User(db.Model):
    __tablename__ = 'ff_users'

    id            = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    username      = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    created_at    = Column(DateTime(timezone=True), default=_utcnow)


class RecipientGroup(db.Model):
    __tablename__ = 'ff_recipient_groups'

    id          = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name        = Column(String(100), nullable=False)
    description = Column(Text)
    addresses   = Column(ARRAY(Text), nullable=False)
    project_id  = Column(UUID(as_uuid=False), ForeignKey('ff_projects.id', ondelete='SET NULL'), nullable=True)
    created_at  = Column(DateTime, default=_utcnow)

    email_configs = relationship('EmailConfig', back_populates='recipient_group')
    project       = relationship('Project', back_populates='recipient_groups')


class EmailProvider(db.Model):
    __tablename__ = 'ff_email_providers'
    __table_args__ = (
        CheckConstraint("provider_type IN ('gmail', 'microsoft365', 'smtp')", name='ck_email_provider_type'),
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
        CheckConstraint("db_type IN ('postgresql', 'oracle')", name='ck_db_connection_type'),
    )

    id         = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name       = Column(String(100), nullable=False)
    db_type    = Column(String(20), nullable=False)
    config     = Column(Text, nullable=False)   # encrypted JSON
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)

    report_configs    = relationship('ReportConfig', back_populates='connection')
    bulk_load_configs = relationship('BulkLoadConfig', back_populates='connection')


class BulkLoadConfig(db.Model):
    __tablename__ = 'ff_bulk_load_configs'

    id                  = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name                = Column(String(255), nullable=False)
    description         = Column(Text)
    connection_id       = Column(UUID(as_uuid=False), ForeignKey('ff_db_connections.id', ondelete='SET NULL'))
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

    id              = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name            = Column(String(255), nullable=False)
    description     = Column(Text)
    connection_id   = Column(UUID(as_uuid=False), ForeignKey('ff_db_connections.id', ondelete='SET NULL'))
    query           = Column(Text, nullable=False)
    format          = Column(String(20), nullable=False)
    template_path   = Column(String(500))
    output_filename = Column(String(500), nullable=False)
    title           = Column(String(255))
    sheet_name      = Column(String(100))
    columns         = Column(ARRAY(Text))
    project_id      = Column(UUID(as_uuid=False), ForeignKey('ff_projects.id', ondelete='SET NULL'), nullable=True)
    created_at      = Column(DateTime(timezone=True), default=_utcnow)
    updated_at      = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    connection = relationship('DbConnection', back_populates='report_configs')
    project    = relationship('Project', back_populates='report_configs')


class EmailConfig(db.Model):
    __tablename__ = 'ff_email_configs'

    id                  = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name                = Column(String(255), nullable=False)
    description         = Column(Text)
    provider_id         = Column(UUID(as_uuid=False), ForeignKey('ff_email_providers.id', ondelete='SET NULL'))
    from_name           = Column(String(255))
    subject             = Column(String(500), nullable=False)
    header_text         = Column(String(500))
    body_template       = Column(Text, nullable=False)
    recipient_group_id  = Column(UUID(as_uuid=False), ForeignKey('ff_recipient_groups.id', ondelete='SET NULL'))
    to_addresses        = Column(ARRAY(Text))
    cc_addresses        = Column(ARRAY(Text))
    bcc_addresses       = Column(ARRAY(Text))
    attachment_max_mb   = Column(Integer, default=10)
    drive_folder_id     = Column(String(255))
    drive_share_message = Column(Text)
    onedrive_folder_id  = Column(String(255))
    project_id          = Column(UUID(as_uuid=False), ForeignKey('ff_projects.id', ondelete='SET NULL'), nullable=True)
    created_at          = Column(DateTime, default=_utcnow)
    updated_at          = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    provider         = relationship('EmailProvider',    back_populates='email_configs')
    recipient_group  = relationship('RecipientGroup',  back_populates='email_configs')
    project          = relationship('Project',         back_populates='email_configs')


class Pipeline(db.Model):
    __tablename__ = 'ff_pipelines'

    id              = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name            = Column(String(255), nullable=False, unique=True)
    description     = Column(Text)
    schedule        = Column(String(100))
    enabled         = Column(Boolean, default=True)
    timeout_minutes = Column(Integer, default=60)
    project_id      = Column(UUID(as_uuid=False), ForeignKey('ff_projects.id', ondelete='SET NULL'), nullable=True)
    created_at      = Column(DateTime(timezone=True), default=_utcnow)
    updated_at      = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    steps          = relationship('PipelineStep', back_populates='pipeline',
                                  order_by='PipelineStep.step_order', cascade='all, delete-orphan')
    variables      = relationship('PipelineVariable', back_populates='pipeline',
                                  cascade='all, delete-orphan')
    runs           = relationship('PipelineRun', back_populates='pipeline')
    webhook_tokens = relationship('WebhookToken', back_populates='pipeline',
                                  cascade='all, delete-orphan')
    project        = relationship('Project', back_populates='pipelines')


class PipelineStep(db.Model):
    __tablename__ = 'ff_pipeline_steps'
    __table_args__ = (
        CheckConstraint(
            "step_type IN ('db_procedure','db_query','report','email','drive_upload','data_load','bulk_load','onedrive_upload','ai_analyze','sftp_transfer')",
            name='ck_step_type',
        ),
        CheckConstraint("on_error IN ('stop', 'continue')", name='ck_on_error'),
        UniqueConstraint('pipeline_id', 'step_order', name='uq_pipeline_step_order'),
    )

    id          = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    pipeline_id = Column(UUID(as_uuid=False), ForeignKey('ff_pipelines.id', ondelete='CASCADE'), nullable=False)
    step_order  = Column(Integer, nullable=False)
    name        = Column(String(255), nullable=False)
    step_type   = Column(String(50), nullable=False)
    config      = Column(JSONB, nullable=False, default=dict)
    on_error    = Column(String(20), default='stop')
    enabled     = Column(Boolean, default=True)

    pipeline = relationship('Pipeline', back_populates='steps')


class PipelineVariable(db.Model):
    __tablename__ = 'ff_pipeline_variables'
    __table_args__ = (
        UniqueConstraint('pipeline_id', 'var_key', name='uq_pipeline_var_key'),
    )

    id          = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    pipeline_id = Column(UUID(as_uuid=False), ForeignKey('ff_pipelines.id', ondelete='CASCADE'), nullable=False)
    var_key     = Column(String(100), nullable=False)
    var_value   = Column(Text, nullable=False)
    is_secret   = Column(Boolean, default=False)

    pipeline = relationship('Pipeline', back_populates='variables')


class PipelineRun(db.Model):
    __tablename__ = 'ff_pipeline_runs'
    __table_args__ = (
        CheckConstraint("status IN ('running','success','failed','cancelled')", name='ck_run_status'),
    )

    id            = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    pipeline_id   = Column(UUID(as_uuid=False), ForeignKey('ff_pipelines.id', ondelete='SET NULL'))
    pipeline_name = Column(String(255), nullable=False)
    status        = Column(String(20), nullable=False)
    started_at    = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    finished_at   = Column(DateTime(timezone=True))
    duration_ms   = Column(Integer)
    triggered_by  = Column(String(50))
    error_step    = Column(String(255))
    error_message = Column(Text)

    pipeline  = relationship('Pipeline', back_populates='runs')
    step_runs = relationship('StepRun', back_populates='pipeline_run', cascade='all, delete-orphan')


class WebhookToken(db.Model):
    """Per-pipeline API tokens for external webhook triggers."""
    __tablename__ = 'ff_webhook_tokens'

    id          = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    pipeline_id = Column(UUID(as_uuid=False), ForeignKey('ff_pipelines.id', ondelete='CASCADE'), nullable=False)
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
