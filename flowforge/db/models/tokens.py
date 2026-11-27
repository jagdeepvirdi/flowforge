from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID

from flowforge.db.models._shared import _utcnow, _uuid, db


class TokenMap(db.Model):
    """Optional reversible mapping for subscriber-identifier tokens (see flowforge/token_store.py).

    The original identifier is stored only as AES-GCM ciphertext under FLOWFORGE_SECRET_KEY. The
    token and kind are plain so the table can be searched; retention is by ``last_seen_at``.
    """
    __tablename__ = 'ff_token_map'

    id           = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    token        = Column(String(64), nullable=False, unique=True)   # tk_<kind>_<32 hex>
    kind         = Column(String(20), nullable=False)                # msisdn | imsi | generic
    ciphertext   = Column(Text, nullable=False)                      # encrypted original identifier
    created_at   = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    last_seen_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)
