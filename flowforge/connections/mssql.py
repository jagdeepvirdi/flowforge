import logging
import time
from typing import Any

from flowforge.connections.base import BaseConnection

logger = logging.getLogger(__name__)

_DEFAULT_DRIVER = 'ODBC Driver 17 for SQL Server'


class MSSQLConnection(BaseConnection):
    """Microsoft SQL Server via pyodbc."""

    db_type = 'mssql'

    def __init__(
        self,
        host: str,
        database: str,
        user: str,
        password: str,
        port: int = 1433,
        driver: str = _DEFAULT_DRIVER,
    ):
        try:
            import pyodbc
        except ImportError:
            raise ImportError(
                "pyodbc is required for MSSQL connections. "
                "Install with: pip install flowforge[mssql]"
            )

        conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={host},{port};"
            f"DATABASE={database};"
            f"UID={user};"
            f"PWD={password};"
            "TrustServerCertificate=yes;"
        )
        self._conn = pyodbc.connect(conn_str, autocommit=False, timeout=10)
        self._conn.setdecoding(pyodbc.SQL_CHAR,  encoding='utf-8')
        self._conn.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-8')
        self._conn.setencoding(encoding='utf-8')
        logger.debug("MSSQL connection opened: %s:%s/%s", host, port, database)

    def execute_procedure(self, name: str, params: dict[str, Any]) -> None:
        placeholders = ', '.join([f'@{k}=?' for k in params])
        sql = f"EXEC {name} {placeholders}"
        cur = self._conn.cursor()
        cur.execute(sql, list(params.values()))
        self._conn.commit()
        cur.close()
        logger.debug("Called MSSQL procedure %s", name)

    def execute_query(self, sql: str, params: tuple = ()) -> list[tuple]:
        cur = self._conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return [tuple(r) for r in rows]

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
        cur.fast_executemany = True
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
            logger.exception("MSSQL connection test failed")
            return False, 0

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:  # nosec B110 — best-effort cleanup, matches other connectors
            pass
