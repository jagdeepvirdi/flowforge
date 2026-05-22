import logging
import time
from typing import Any

from flowforge.connections.base import BaseConnection

logger = logging.getLogger(__name__)


class OracleConnection(BaseConnection):
    db_type = 'oracle'

    def __init__(self, host: str, port: int, service_name: str, user: str, password: str):
        try:
            import oracledb
        except ImportError:
            raise ImportError(
                "python-oracledb is required for Oracle connections. "
                "Install with: pip install flowforge[oracle]"
            )
        # Thin mode: pure Python, no Oracle Instant Client required.
        # To use thick mode (for advanced Oracle features), call
        # oracledb.init_oracle_client() before creating the pool.
        self._pool = oracledb.create_pool(
            user=user,
            password=password,
            dsn=f"{host}:{port}/{service_name}",
            min=1,
            max=5,
            increment=1,
        )
        self._conn = self._pool.acquire()
        self._conn.autocommit = False
        logger.debug("Oracle connection acquired for %s:%s/%s", host, port, service_name)

    def execute_procedure(self, name: str, params: dict[str, Any]) -> None:
        binds = ", ".join([f":{k}" for k in params])
        sql = f"BEGIN {name}({binds}); END;"
        with self._conn.cursor() as cur:
            cur.arraysize = 1000
            cur.execute(sql, params)
        self._conn.commit()
        logger.debug("Called Oracle procedure %s", name)

    def execute_query(self, sql: str, params: tuple = ()) -> list[tuple]:
        with self._conn.cursor() as cur:
            cur.arraysize = 1000
            cur.execute(sql, params)
            rows = cur.fetchall()
        return [
            tuple(col.read() if hasattr(col, "read") else col for col in row)
            for row in rows
        ]

    def execute_query_with_columns(self, sql: str, params: tuple = ()) -> tuple[list[tuple], list[str]]:
        with self._conn.cursor() as cur:
            cur.arraysize = 1000
            cur.execute(sql, params)
            columns = [desc[0] for desc in cur.description] if cur.description else []
            rows = cur.fetchall()
        return [
            tuple(col.read() if hasattr(col, "read") else col for col in row)
            for row in rows
        ], columns

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
        return ', '.join([f':{i + 1}' for i in range(n)])

    def test(self) -> tuple[bool, int]:
        start = time.monotonic()
        try:
            self.execute_query("SELECT 1 FROM DUAL")
            return True, int((time.monotonic() - start) * 1000)
        except Exception as e:
            logger.error("Oracle connection test failed: %s", e)
            return False, 0

    def close(self) -> None:
        self._pool.release(self._conn)
