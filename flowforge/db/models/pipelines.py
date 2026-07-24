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

from flowforge.db.models._shared import (
    _CASCADE,
    _FF_PIPELINES_ID,
    _FF_PROJECTS_ID,
    _SET_NULL,
    _utcnow,
    _uuid,
    db,
)


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
