from sqlalchemy import Column, DateTime, Integer, String

from flowforge.db.models._shared import _utcnow, db


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
