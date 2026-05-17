import logging
import time
from typing import Any

from flowforge.connections.base import BaseConnection

logger = logging.getLogger(__name__)


class OracleConnection(BaseConnection):
    def __init__(self, host: str, port: int, service_name: str, user: str, password: str):
        try:
            import cx_Oracle
        except ImportError:
            raise ImportError(
                "cx_Oracle is required for Oracle connections. "
                "Install Oracle Instant Client first, then: pip install flowforge[oracle]"
            )
        dsn = cx_Oracle.makedsn(host, port, service_name=service_name)
        self._pool = cx_Oracle.SessionPool(
            user=user, password=password, dsn=dsn,
            min=1, max=5, increment=1, threaded=True,
        )
        self._conn = self._pool.acquire()
        self._conn.autocommit = False
        logger.debug("Oracle connection acquired for %s:%s/%s", host, port, service_name)

    def execute_procedure(self, name: str, params: dict[str, Any]) -> None:
        # Supports Oracle package syntax: package.procedure
        binds = ', '.join([f':{k}' for k in params])
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
        # Read LOB values before cursor close
        return [
            tuple(col.read() if hasattr(col, 'read') else col for col in row)
            for row in rows
        ]

    def execute_write(self, sql: str, params: tuple = ()) -> int:
        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.rowcount
        self._conn.commit()
        return rows

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
