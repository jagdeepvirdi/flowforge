"""Load a database connection from the FlowForge config DB.

Dispatch by `db_type` goes through `connections_registry` (see
flowforge/registry.py) instead of an if/elif chain. Each built-in entry stores
the connection class's dotted path (not the already-imported class object)
plus a small `cfg -> kwargs` function — the class itself is only imported, and
its optional third-party driver (oracledb, pymysql, pyodbc, ...) only pulled
in, at the moment a connection of that type is actually built.

Plugin-defined connections (registered by engine/loader.py's plugin scanner —
see docs/TASKS.md Phase 13.3) register the class itself instead of a
(dotted_path, kwargs_fn) tuple, since the class is already imported by the
scanner. Such classes must define a `from_config(cls, cfg: dict)` classmethod
— see get_connection() below for the two dispatch paths.
"""
import importlib
from typing import Any, Callable

from flowforge.connections.base import BaseConnection
from flowforge.registry import IntegrationSpec, Registry

connections_registry = Registry('connections')


def _register(key: str, dotted_path: str, kwargs_fn: Callable[[dict], dict],
              display_name: str, requires: str | None = None) -> None:
    connections_registry.register_spec(
        IntegrationSpec(key=key, display_name=display_name, requires=requires),
        (dotted_path, kwargs_fn),
    )


_register(
    'postgresql', 'flowforge.connections.postgres.PostgreSQLConnection',
    lambda cfg: dict(
        host=cfg['host'],
        database=cfg['database'],
        user=cfg.get('user') or cfg.get('username', ''),
        password=cfg['password'],
        port=int(cfg.get('port', 5432)),
    ),
    display_name='PostgreSQL',
)

_register(
    'oracle', 'flowforge.connections.oracle.OracleConnection',
    lambda cfg: dict(
        host=cfg['host'],
        port=int(cfg.get('port', 1521)),
        service_name=cfg.get('service_name') or cfg.get('database', ''),
        user=cfg.get('user') or cfg.get('username', ''),
        password=cfg['password'],
    ),
    display_name='Oracle', requires='oracle',
)

_register(
    'mysql', 'flowforge.connections.mysql.MySQLConnection',
    lambda cfg: dict(
        host=cfg['host'],
        database=cfg.get('database', ''),
        user=cfg.get('user') or cfg.get('username', ''),
        password=cfg['password'],
        port=int(cfg.get('port', 3306)),
    ),
    display_name='MySQL / MariaDB', requires='mysql',
)

_register(
    'mssql', 'flowforge.connections.mssql.MSSQLConnection',
    lambda cfg: dict(
        host=cfg['host'],
        database=cfg.get('database', ''),
        user=cfg.get('user') or cfg.get('username', ''),
        password=cfg['password'],
        port=int(cfg.get('port', 1433)),
        driver=cfg.get('driver', 'ODBC Driver 17 for SQL Server'),
    ),
    display_name='Microsoft SQL Server', requires='mssql',
)

_register(
    'odbc', 'flowforge.connections.odbc.ODBCConnection',
    lambda cfg: dict(
        dsn=cfg.get('dsn', ''),
        connection_string=cfg.get('connection_string', ''),
    ),
    display_name='Generic ODBC', requires='mssql',
)

_register(
    'redshift', 'flowforge.connections.redshift.RedshiftConnection',
    lambda cfg: dict(
        host=cfg['host'],
        database=cfg.get('database', ''),
        user=cfg.get('user') or cfg.get('username', ''),
        password=cfg['password'],
        port=int(cfg.get('port', 5439)),
    ),
    display_name='Amazon Redshift',
)

_register(
    'snowflake', 'flowforge.connections.snowflake.SnowflakeConnection',
    lambda cfg: dict(
        account=cfg.get('account', ''),
        user=cfg.get('user') or cfg.get('username', ''),
        password=cfg['password'],
        warehouse=cfg.get('warehouse', ''),
        database=cfg.get('database', ''),
        schema=cfg.get('schema', ''),
        role=cfg.get('role', ''),
    ),
    display_name='Snowflake', requires='snowflake',
)

_register(
    'bigquery', 'flowforge.connections.bigquery.BigQueryConnection',
    lambda cfg: dict(
        project_id=cfg.get('project_id', ''),
        dataset=cfg.get('dataset', ''),
        credentials_json=cfg.get('credentials_json', ''),
    ),
    display_name='Google BigQuery', requires='bigquery',
)

# Snapshot of built-in db_types, taken right after registration above —
# lets the plugin loader's test-reset helper drop only plugin-added entries.
BUILTIN_DB_TYPES = frozenset(connections_registry.list())


def get_connection(connection_id: str) -> BaseConnection:
    """Return the appropriate BaseConnection subclass for a db_connections row."""
    from flowforge.crypto import decrypt_config
    from flowforge.db.models import DbConnection, db

    row = db.session.get(DbConnection, connection_id)
    if not row:
        raise ValueError(f"DB connection not found: {connection_id}")

    if row.db_type not in connections_registry:
        raise ValueError(f"Unsupported db_type: {row.db_type}")

    cfg = decrypt_config(row.config)
    entry = connections_registry.get(row.db_type)

    if isinstance(entry, tuple):
        dotted_path, kwargs_fn = entry
        module_path, class_name = dotted_path.rsplit('.', 1)
        cls: Any = getattr(importlib.import_module(module_path), class_name)
        return cls(**kwargs_fn(cfg))

    # Plugin-registered connection: `entry` is the class itself.
    if not hasattr(entry, 'from_config'):
        raise ValueError(
            f"Plugin connection '{row.db_type}' ({entry.__name__}) must define a "
            "from_config(cls, cfg) classmethod"
        )
    return entry.from_config(cfg)
