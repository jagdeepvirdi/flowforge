import logging
import time
from typing import Any

from flowforge.connections.base import BaseConnection

logger = logging.getLogger(__name__)


class ODBCConnection(BaseConnection):
    """Generic ODBC connection via pyodbc.

    Config accepts either:
      dsn             — a pre-configured ODBC Data Source Name
      connection_string — a full pyodbc connection string
                         (e.g. "Driver={...};Server=...;Database=...;UID=...;PWD=...")
    """

    db_type = 'odbc'

    def __init__(self, dsn: str = '', connection_string: str = ''):
        try:
            import pyodbc
        except ImportError:
            raise ImportError(
                "pyodbc is required for ODBC connections. "
                "Install with: pip install flowforge[mssql]"
            )

        if not dsn and not connection_string:
            raise ValueError("ODBCConnection requires either 'dsn' or 'connection_string'")

        if dsn:
            self._conn = pyodbc.connect(f'DSN={dsn}', autocommit=False, timeout=10)
        else:
            self._conn = pyodbc.connect(connection_string, autocommit=False, timeout=10)

        logger.debug("ODBC connection opened (dsn=%r)", dsn or '<connection_string>')

    def execute_procedure(self, name: str, params: dict[str, Any]) -> None:
        placeholders = ', '.join(['?'] * len(params))
        sql = f"{{CALL {name} ({placeholders})}}"
        cur = self._conn.cursor()
        cur.execute(sql, list(params.values()))
        self._conn.commit()
        cur.close()
        logger.debug("Called ODBC procedure %s", name)

    def execute_query(self, sql: str, params: tuple = ()) -> list[tuple]:
        cur = self._conn.cursor()
        cur.execute(sql, params)
        rows = [tuple(r) for r in cur.fetchall()]
        cur.close()
        return rows

    def execute_query_with_columns(self, sql: str, params: tuple = ()) -> tuple[list[tuple], list[str]]:
        cur = self._conn.cursor()
        cur.execute(sql, params)
        columns = [col[0] for col in cur.description] if cur.description else []
        rows = [tuple(r) for r in cur.fetchall()]
        cur.close()
        return rows, columns

    def execute_write(self, sql: str, params: tuple = ()) -> int:
        cur = self._conn.cursor()
        cur.execute(sql, params)
        count = cur.rowcount
        self._conn.commit()
        cur.close()
        return count

    def execute_many(self, sql: str, rows: list[tuple]) -> int:
        cur = self._conn.cursor()
        cur.executemany(sql, rows)
        count = cur.rowcount
        self._conn.commit()
        cur.close()
        return count

    @staticmethod
    def make_placeholders(n: int) -> str:
        return ', '.join(['?'] * n)

    def test(self) -> tuple[bool, int]:
        start = time.monotonic()
        try:
            self.execute_query("SELECT 1")
            return True, int((time.monotonic() - start) * 1000)
        except Exception:
            logger.exception("ODBC connection test failed")
            return False, 0

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:  # nosec B110 — best-effort cleanup, matches other connectors
            pass
