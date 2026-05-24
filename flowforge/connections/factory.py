"""Load a database connection from the FlowForge config DB."""
from flowforge.connections.base import BaseConnection


def get_connection(connection_id: str) -> BaseConnection:
    """Return the appropriate BaseConnection subclass for a db_connections row."""
    from flowforge.crypto import decrypt_config
    from flowforge.db.models import DbConnection, db

    row = db.session.get(DbConnection, connection_id)
    if not row:
        raise ValueError(f"DB connection not found: {connection_id}")

    cfg = decrypt_config(row.config)

    if row.db_type == 'postgresql':
        from flowforge.connections.postgres import PostgreSQLConnection
        return PostgreSQLConnection(
            host=cfg['host'],
            database=cfg['database'],
            user=cfg.get('user') or cfg.get('username', ''),
            password=cfg['password'],
            port=int(cfg.get('port', 5432)),
        )

    if row.db_type == 'oracle':
        from flowforge.connections.oracle import OracleConnection
        return OracleConnection(
            host=cfg['host'],
            port=int(cfg.get('port', 1521)),
            service_name=cfg.get('service_name') or cfg.get('database', ''),
            user=cfg.get('user') or cfg.get('username', ''),
            password=cfg['password'],
        )

    raise ValueError(f"Unsupported db_type: {row.db_type}")
