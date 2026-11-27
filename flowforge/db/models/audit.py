from sqlalchemy import BigInteger, Boolean, Column, DateTime, String
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

    # Tamper-evident chain (flowforge/audit_chain.py). NULL seq = a legacy / unchained row.
    seq            = Column(BigInteger, unique=True)               # 1, 2, 3 ... one chain
    prev_hash      = Column(String(64))                            # row_hash of seq - 1 (zeros for seq 1)
    content_digest = Column(String(64))                            # sha256 of the row's content when written
    row_hash       = Column(String(64))                            # HMAC(key, seq | prev_hash | content_digest)
    anonymized     = Column(Boolean, nullable=False, default=False, server_default='false')  # GDPR-purged
