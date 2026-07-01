import logging
import time
from typing import Any

from flowforge.connections.base import BaseConnection

logger = logging.getLogger(__name__)


class SnowflakeConnection(BaseConnection):
    db_type = 'snowflake'

    def __init__(self, account: str, user: str, password: str, warehouse: str = '',
                 database: str = '', schema: str = '', role: str = ''):
        try:
            import snowflake.connector
        except ImportError:
            raise ImportError(
                "snowflake-connector-python is required for Snowflake connections. "
                "Install with: pip install flowforge[snowflake]"
            )
        self._conn = snowflake.connector.connect(
            account=account,
            user=user,
            password=password,
            warehouse=warehouse or None,
            database=database or None,
            schema=schema or None,
            role=role or None,
        )
        logger.debug("Snowflake connection opened for account %s", account)

    def execute_procedure(self, name: str, params: dict[str, Any]) -> None:
        placeholders = ', '.join(['%s'] * len(params))
        sql = f"CALL {name}({placeholders})"
        with self._conn.cursor() as cur:
            cur.execute(sql, list(params.values()))
        self._conn.commit()
        logger.debug("Called Snowflake procedure %s", name)

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
            logger.exception("Snowflake connection test failed")
            return False, 0

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass
