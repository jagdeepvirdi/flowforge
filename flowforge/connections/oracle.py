import logging
import time
from collections.abc import Iterator
from typing import Any

from flowforge.connections.base import BaseConnection

logger = logging.getLogger(__name__)

# Module-level pool registry keyed by (host, port, service_name, user, password_hash).
# Mirrors the postgres.py approach so a multi-step Oracle pipeline reuses one pool.
_pools: dict[tuple, Any] = {}


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
        key = (host, port, service_name, user, password)
        if key not in _pools:
            # Thin mode: pure Python, no Oracle Instant Client required.
            # To use thick mode (for advanced Oracle features), call
            # oracledb.init_oracle_client() before creating the pool.
            _pools[key] = oracledb.create_pool(
                user=user,
                password=password,
                dsn=f"{host}:{port}/{service_name}",
                min=1,
                max=5,
                increment=1,
                tcp_connect_timeout=5,
            )
            logger.debug("Created Oracle pool for %s:%s/%s", host, port, service_name)
        self._pool = _pools[key]
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

    def execute_query_with_columns_chunked(
        self, sql: str, params: tuple = (), chunk_size: int = 1000,
    ) -> tuple[list[str], Iterator[tuple]]:
        """Real streaming: iterating an oracledb cursor directly (rather than
        calling fetchall()) already fetches in arraysize-sized batches from the
        server without materializing the whole result client-side."""
        cur = self._conn.cursor()
        cur.arraysize = chunk_size
        cur.execute(sql, params)
        columns = [desc[0] for desc in cur.description] if cur.description else []
        return columns, self._stream_and_close(cur)

    @staticmethod
    def _stream_and_close(cur) -> Iterator[tuple]:
        try:
            for row in cur:
                yield tuple(col.read() if hasattr(col, "read") else col for col in row)
        finally:
            cur.close()

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
        except Exception:
            logger.exception("Oracle connection test failed")
            return False, 0

    def close(self) -> None:
        self._pool.release(self._conn)
