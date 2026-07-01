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

    if row.db_type == 'mysql':
        from flowforge.connections.mysql import MySQLConnection
        return MySQLConnection(
            host=cfg['host'],
            database=cfg.get('database', ''),
            user=cfg.get('user') or cfg.get('username', ''),
            password=cfg['password'],
            port=int(cfg.get('port', 3306)),
        )

    if row.db_type == 'mssql':
        from flowforge.connections.mssql import MSSQLConnection
        return MSSQLConnection(
            host=cfg['host'],
            database=cfg.get('database', ''),
            user=cfg.get('user') or cfg.get('username', ''),
            password=cfg['password'],
            port=int(cfg.get('port', 1433)),
            driver=cfg.get('driver', 'ODBC Driver 17 for SQL Server'),
        )

    if row.db_type == 'odbc':
        from flowforge.connections.odbc import ODBCConnection
        return ODBCConnection(
            dsn=cfg.get('dsn', ''),
            connection_string=cfg.get('connection_string', ''),
        )

    if row.db_type == 'redshift':
        from flowforge.connections.redshift import RedshiftConnection
        return RedshiftConnection(
            host=cfg['host'],
            database=cfg.get('database', ''),
            user=cfg.get('user') or cfg.get('username', ''),
            password=cfg['password'],
            port=int(cfg.get('port', 5439)),
        )

    if row.db_type == 'snowflake':
        from flowforge.connections.snowflake import SnowflakeConnection
        return SnowflakeConnection(
            account=cfg.get('account', ''),
            user=cfg.get('user') or cfg.get('username', ''),
            password=cfg['password'],
            warehouse=cfg.get('warehouse', ''),
            database=cfg.get('database', ''),
            schema=cfg.get('schema', ''),
            role=cfg.get('role', ''),
        )

    if row.db_type == 'bigquery':
        from flowforge.connections.bigquery import BigQueryConnection
        return BigQueryConnection(
            project_id=cfg.get('project_id', ''),
            dataset=cfg.get('dataset', ''),
            credentials_json=cfg.get('credentials_json', ''),
        )

    raise ValueError(f"Unsupported db_type: {row.db_type}")
