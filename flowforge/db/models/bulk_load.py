from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from flowforge.db.models._shared import _SET_NULL, _utcnow, _uuid, db


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
