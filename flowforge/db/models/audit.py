from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from flowforge.db.models._shared import _utcnow, _uuid, db


class AuditLog(db.Model):
    __tablename__ = 'ff_audit_log'

    id           = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    timestamp    = Column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)
    action       = Column(String(50), nullable=False, index=True)  # e.g., LOGIN, LOGOUT, PIPELINE_RUN, CONFIG_CREATED
    username     = Column(String(255), nullable=False, index=True) # Usually the doer
    user_id      = Column(UUID(as_uuid=False))                     # Nullable for system actions or legacy
    ip_address   = Column(String(45))                              # IPv6 max len
    details      = Column(JSONB, default=dict, nullable=False)     # e.g. pipeline_id, step_name, etc.
