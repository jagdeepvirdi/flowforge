"""Unit tests for flowforge/connections/base.py's concrete default methods."""


def _make_minimal_connection(rows, columns):
    """A minimal BaseConnection subclass implementing only the abstract methods,
    to exercise the base class's concrete execute_query_with_columns_chunked
    fallback untouched."""
    from flowforge.connections.base import BaseConnection

    class _MinimalConnection(BaseConnection):
        def execute_procedure(self, name, params):
            raise NotImplementedError

        def execute_query(self, sql, params=()):
            return rows

        def execute_query_with_columns(self, sql, params=()):
            return rows, columns

        def execute_write(self, sql, params=()):
            raise NotImplementedError

        def execute_many(self, sql, rows):
            raise NotImplementedError

        def make_placeholders(self, n):
            return ', '.join(['%s'] * n)

        def test(self):
            return True, 0

        def close(self):
            pass

    return _MinimalConnection()


def test_default_chunked_falls_back_to_eager_query():
    """A connection type with no streaming override still works — just without
    the memory-saving benefit, per the base class docstring."""
    conn = _make_minimal_connection([(1, 'a'), (2, 'b')], ['id', 'name'])
    cols, row_iter = conn.execute_query_with_columns_chunked('SELECT 1')
    assert cols == ['id', 'name']
    assert list(row_iter) == [(1, 'a'), (2, 'b')]


def test_default_chunked_returns_an_iterator_not_a_list():
    """Callers should be able to treat the result uniformly whether or not the
    connection type has a real streaming override."""
    conn = _make_minimal_connection([(1,)], ['id'])
    _, row_iter = conn.execute_query_with_columns_chunked('SELECT 1')
    assert not isinstance(row_iter, list)
    assert hasattr(row_iter, '__next__')


def test_default_chunked_zero_rows():
    conn = _make_minimal_connection([], ['id'])
    cols, row_iter = conn.execute_query_with_columns_chunked('SELECT 1 WHERE 1=0')
    assert cols == ['id']
    assert list(row_iter) == []
