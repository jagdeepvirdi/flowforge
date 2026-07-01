import logging
import time
from typing import Any

from flowforge.connections.base import BaseConnection

logger = logging.getLogger(__name__)

_pools: dict[tuple, Any] = {}


class MySQLConnection(BaseConnection):
    db_type = 'mysql'

    def __init__(self, host: str, database: str, user: str, password: str, port: int = 3306):
        try:
            import pymysql
        except ImportError:
            raise ImportError(
                "PyMySQL is required for MySQL/MariaDB connections. "
                "Install with: pip install flowforge[mysql]"
            )

        key = (host, port, database, user, password)
        if key not in _pools:
            _pools[key] = {
                'host': host, 'port': port, 'database': database,
                'user': user, 'password': password,
            }
            logger.debug("Registered MySQL connection config for %s:%s/%s", host, port, database)

        cfg = _pools[key]
        import pymysql
        self._conn = pymysql.connect(
            host=cfg['host'],
            port=cfg['port'],
            database=cfg['database'],
            user=cfg['user'],
            password=cfg['password'],
            autocommit=False,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.Cursor,
        )

    def execute_procedure(self, name: str, params: dict[str, Any]) -> None:
        with self._conn.cursor() as cur:
            cur.callproc(name, list(params.values()))
        self._conn.commit()
        logger.debug("Called MySQL procedure %s", name)

    def execute_query(self, sql: str, params: tuple = ()) -> list[tuple]:
        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())

    def execute_query_with_columns(self, sql: str, params: tuple = ()) -> tuple[list[tuple], list[str]]:
        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            columns = [desc[0] for desc in cur.description] if cur.description else []
            return list(cur.fetchall()), columns

    def execute_write(self, sql: str, params: tuple = ()) -> int:
        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.rowcount
        self._conn.commit()
        return rows

    def execute_many(self, sql: str, rows: list[tuple]) -> int:
        with self._conn.cursor() as cur:
            cur.executemany(sql, rows)
            count = cur.rowcount
        self._conn.commit()
        return count

    def make_placeholders(self, n: int) -> str:
        return ', '.join(['%s'] * n)

    def test(self) -> tuple[bool, int]:
        start = time.monotonic()
        try:
            self.execute_query("SELECT 1")
            return True, int((time.monotonic() - start) * 1000)
        except Exception:
            logger.exception("MySQL connection test failed")
            return False, 0

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:  # nosec B110 — best-effort cleanup, matches other connectors
            pass
