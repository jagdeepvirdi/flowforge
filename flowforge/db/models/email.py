from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from flowforge.db.models._shared import _FF_PROJECTS_ID, _SET_NULL, _utcnow, _uuid, db


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
