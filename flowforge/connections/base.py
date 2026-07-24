from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any


class BaseConnection(ABC):
    @abstractmethod
    def execute_procedure(self, name: str, params: dict[str, Any]) -> None: ...

    @abstractmethod
    def execute_query(self, sql: str, params: tuple = ()) -> list[tuple]: ...

    @abstractmethod
    def execute_query_with_columns(self, sql: str, params: tuple = ()) -> tuple[list[tuple], list[str]]: ...

    def execute_query_with_columns_chunked(
        self, sql: str, params: tuple = (), chunk_size: int = 5000,
    ) -> tuple[list[str], Iterator[tuple]]:
        """Like execute_query_with_columns, but the row iterator is meant to be
        consumed lazily instead of fully materialized — for report generation
        and other paths where a multi-million-row result would otherwise be
        held entirely in memory before the first byte is written out.

        Concrete default: not actually streaming (falls back to the regular
        fetch-everything-then-iterate path) — correct for every connection
        type, but doesn't reduce memory usage. postgres.py (named server-side
        cursor) and oracle.py (batch cursor iteration instead of fetchall())
        override this with a real streaming implementation; every other
        connection type inherits this default until it gets one too.
        """
        rows, columns = self.execute_query_with_columns(sql, params)
        return columns, iter(rows)

    @abstractmethod
    def execute_write(self, sql: str, params: tuple = ()) -> int: ...

    @abstractmethod
    def execute_many(self, sql: str, rows: list[tuple]) -> int: ...

    @staticmethod
    @abstractmethod
    def make_placeholders(n: int) -> str: ...

    @abstractmethod
    def test(self) -> tuple[bool, int]: ...

    @abstractmethod
    def close(self) -> None: ...

    @property
    def raw_connection(self) -> Any:
        """Underlying DB-API connection object, for callers that need cursor-level
        control beyond execute_write/execute_many/execute_query — e.g. COPY FROM
        STDIN, or a SAVEPOINT-based transaction that must not auto-commit between
        statements (see flowforge/steps/bulk_load.py). Concrete subclasses built on
        a traditional DB-API connection store it as self._conn; connections built
        on a client library without cursor-level DB-API semantics (e.g. BigQuery)
        don't, and callers needing raw access get a clear error instead of an
        unrelated AttributeError.
        """
        conn = getattr(self, '_conn', None)
        if conn is None:
            raise NotImplementedError(
                f'{type(self).__name__} does not expose a raw DB-API connection.'
            )
        return conn

    def __enter__(self) -> 'BaseConnection':
        return self

    def __exit__(self, *_) -> None:
        self.close()
