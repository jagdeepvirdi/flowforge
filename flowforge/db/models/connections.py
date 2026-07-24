from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from flowforge.db.models._shared import _utcnow, _uuid, db


class DbConnection(db.Model):
    __tablename__ = 'ff_db_connections'
    __table_args__ = (
        CheckConstraint(
            "db_type IN ('postgresql', 'oracle', 'mysql', 'mssql', 'odbc', 'redshift', 'snowflake', 'bigquery')",
            name='ck_db_connection_type',
        ),
    )

    id         = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name       = Column(String(100), nullable=False)
    db_type    = Column(String(20), nullable=False)
    config     = Column(Text, nullable=False)   # encrypted JSON
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    report_configs    = relationship('ReportConfig', back_populates='connection')
    bulk_load_configs = relationship('BulkLoadConfig', back_populates='connection')


class SSHConnection(db.Model):
    __tablename__ = 'ff_ssh_connections'

    id         = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name       = Column(String(100), nullable=False)
    config     = Column(Text, nullable=False)   # encrypted JSON (host, port, username, password, key_path)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
