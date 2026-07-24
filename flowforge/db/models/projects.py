from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from flowforge.db.models._shared import _CASCADE, _utcnow, _uuid, db


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
