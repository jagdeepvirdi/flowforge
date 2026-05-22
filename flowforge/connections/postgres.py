import logging
import time
from typing import Any

import psycopg2
from psycopg2 import pool

from flowforge.connections.base import BaseConnection

logger = logging.getLogger(__name__)

# Module-level pool registry keyed by (host, port, database, user)
_pools: dict[tuple, pool.ThreadedConnectionPool] = {}


class PostgreSQLConnection(BaseConnection):
    db_type = 'postgresql'

    def __init__(self, host: str, database: str, user: str, password: str, port: int = 5432):
        key = (host, port, database, user)
        if key not in _pools:
            _pools[key] = pool.ThreadedConnectionPool(
                1, 5, host=host, port=port, database=database, user=user, password=password
            )
            logger.debug("Created connection pool for %s:%s/%s", host, port, database)
        self._pool = _pools[key]
        self._conn = self._pool.getconn()

    def execute_procedure(self, name: str, params: dict[str, Any]) -> None:
        placeholders = ', '.join(['%s'] * len(params))
        sql = f"CALL {name}({placeholders})"
        with self._conn.cursor() as cur:
            cur.execute(sql, list(params.values()))
        self._conn.commit()
        logger.debug("Called procedure %s", name)

    def execute_query(self, sql: str, params: tuple = ()) -> list[tuple]:
        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def execute_query_with_columns(self, sql: str, params: tuple = ()) -> tuple[list[tuple], list[str]]:
        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            columns = [desc[0] for desc in cur.description] if cur.description else []
            return cur.fetchall(), columns

    def execute_write(self, sql: str, params: tuple = ()) -> int:
        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.rowcount
        self._conn.commit()
        return rows

    def execute_many(self, sql: str, rows: list[tuple]) -> int:
        from psycopg2.extras import execute_batch
        with self._conn.cursor() as cur:
            execute_batch(cur, sql, rows, page_size=1000)
        self._conn.commit()
        return len(rows)

    def make_placeholders(self, n: int) -> str:
        return ', '.join(['%s'] * n)

    def test(self) -> tuple[bool, int]:
        start = time.monotonic()
        try:
            self.execute_query("SELECT 1")
            return True, int((time.monotonic() - start) * 1000)
        except Exception as e:
            logger.error("PostgreSQL connection test failed: %s", e)
            return False, 0

    def close(self) -> None:
        self._pool.putconn(self._conn)
