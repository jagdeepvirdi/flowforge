from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from flowforge.db.models._shared import _FF_PROJECTS_ID, _SET_NULL, _utcnow, _uuid, db


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
