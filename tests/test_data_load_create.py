"""
Tests for DataLoadStep.create_if_missing, _table_exists, _create_table,
and _infer_col_type.

All DB calls are mocked — no live database required for this module.
"""
from datetime import date, datetime
from unittest.mock import MagicMock, patch

from flowforge.steps.data_load import DataLoadStep, _infer_col_type

# ─────────────────────────────────────────────────────────────────────────────
# _infer_col_type — PostgreSQL
# ─────────────────────────────────────────────────────────────────────────────

def test_infer_bool_pg():
    assert _infer_col_type([True, False, True], 'postgresql') == 'BOOLEAN'


def test_infer_int_pg():
    assert _infer_col_type([1, 42, 999], 'postgresql') == 'BIGINT'


def test_infer_float_pg():
    assert _infer_col_type([1.5, 2.0, 3.14], 'postgresql') == 'NUMERIC'


def test_infer_datetime_object_pg():
    vals = [datetime(2026, 1, 1), datetime(2026, 6, 15, 12, 0)]
    assert _infer_col_type(vals, 'postgresql') == 'TIMESTAMP'


def test_infer_date_object_pg():
    vals = [date(2026, 1, 1), date(2026, 6, 15)]
    assert _infer_col_type(vals, 'postgresql') == 'DATE'


def test_infer_text_pg():
    assert _infer_col_type(['alpha', 'beta', 'gamma'], 'postgresql') == 'TEXT'


def test_infer_empty_pg():
    assert _infer_col_type([], 'postgresql') == 'TEXT'


def test_infer_all_null_pg():
    assert _infer_col_type([None, None], 'postgresql') == 'TEXT'


def test_infer_string_bool_pg():
    assert _infer_col_type(['true', 'false', 'TRUE'], 'postgresql') == 'BOOLEAN'


def test_infer_string_int_pg():
    assert _infer_col_type(['1', '42', '999'], 'postgresql') == 'BIGINT'


def test_infer_string_float_pg():
    assert _infer_col_type(['1.5', '2.0', '3.14'], 'postgresql') == 'NUMERIC'


def test_infer_string_timestamp_pg():
    vals = ['2026-01-01 00:00:00', '2026-06-15T12:00']
    assert _infer_col_type(vals, 'postgresql') == 'TIMESTAMP'


def test_infer_string_date_pg():
    vals = ['2026-01-01', '2026-06-15']
    assert _infer_col_type(vals, 'postgresql') == 'DATE'


def test_infer_mixed_int_float_returns_numeric_pg():
    # Mix of int and float: neither all-int nor all-float Python branch matches,
    # but '1', '2.5', '3' all parse as floats in the string path → NUMERIC.
    assert _infer_col_type([1, 2.5, 3], 'postgresql') == 'NUMERIC'


# ─────────────────────────────────────────────────────────────────────────────
# _infer_col_type — Oracle
# ─────────────────────────────────────────────────────────────────────────────

def test_infer_bool_oracle():
    assert _infer_col_type([True, False], 'oracle') == 'NUMBER(1)'


def test_infer_int_oracle():
    assert _infer_col_type([1, 2, 3], 'oracle') == 'NUMBER(18)'


def test_infer_float_oracle():
    assert _infer_col_type([1.5, 2.5], 'oracle') == 'NUMBER'


def test_infer_text_oracle():
    assert _infer_col_type(['hello', 'world'], 'oracle') == 'VARCHAR2(4000)'


def test_infer_empty_oracle():
    assert _infer_col_type([], 'oracle') == 'VARCHAR2(4000)'


def test_infer_date_same_for_oracle():
    vals = [date(2026, 1, 1), date(2026, 6, 15)]
    assert _infer_col_type(vals, 'oracle') == 'DATE'


def test_infer_timestamp_same_for_oracle():
    vals = [datetime(2026, 1, 1), datetime(2026, 6, 15)]
    assert _infer_col_type(vals, 'oracle') == 'TIMESTAMP'


# ─────────────────────────────────────────────────────────────────────────────
# _table_exists — catalog queries
# ─────────────────────────────────────────────────────────────────────────────

def _make_conn(db_type='postgresql', rows=None):
    conn = MagicMock()
    conn.db_type = db_type
    conn.execute_query.return_value = rows if rows is not None else []
    return conn


def test_table_exists_pg_returns_true():
    conn = _make_conn('postgresql', rows=[(1,)])
    step = DataLoadStep(name='t', config={})
    assert step._table_exists(conn, 'public.my_table') is True
    conn.execute_query.assert_called_once_with(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name = %s AND table_schema = %s",
        ('my_table', 'public'),
    )


def test_table_exists_pg_returns_false():
    conn = _make_conn('postgresql', rows=[])
    step = DataLoadStep(name='t', config={})
    assert step._table_exists(conn, 'public.missing_table') is False


def test_table_exists_pg_no_schema_defaults_to_public():
    conn = _make_conn('postgresql', rows=[])
    step = DataLoadStep(name='t', config={})
    step._table_exists(conn, 'bare_table')
    conn.execute_query.assert_called_once_with(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name = %s AND table_schema = %s",
        ('bare_table', 'public'),
    )


def test_table_exists_oracle_no_schema():
    conn = _make_conn('oracle', rows=[(1,)])
    step = DataLoadStep(name='t', config={})
    assert step._table_exists(conn, 'MY_TABLE') is True
    conn.execute_query.assert_called_once_with(
        "SELECT 1 FROM user_tables WHERE table_name = UPPER(:1)",
        ('MY_TABLE',),
    )


def test_table_exists_oracle_with_schema():
    conn = _make_conn('oracle', rows=[(1,)])
    step = DataLoadStep(name='t', config={})
    assert step._table_exists(conn, 'MYSCHEMA.MY_TABLE') is True
    conn.execute_query.assert_called_once_with(
        "SELECT 1 FROM all_tables "
        "WHERE table_name = UPPER(:1) AND owner = UPPER(:2)",
        ('MY_TABLE', 'MYSCHEMA'),
    )


def test_table_exists_returns_false_on_exception():
    conn = MagicMock()
    conn.db_type = 'postgresql'
    conn.execute_query.side_effect = RuntimeError("connection broken")
    step = DataLoadStep(name='t', config={})
    assert step._table_exists(conn, 'public.some_table') is False


# ─────────────────────────────────────────────────────────────────────────────
# _create_table — DDL generation
# ─────────────────────────────────────────────────────────────────────────────

def test_create_table_pg_basic():
    conn = _make_conn('postgresql')
    step = DataLoadStep(name='t', config={})
    columns = ['id', 'name', 'amount']
    rows = [(1, 'Alice', 9.99), (2, 'Bob', 19.99)]
    step._create_table(conn, 'public.test_tbl', columns, rows)
    ddl = conn.execute_write.call_args[0][0]
    assert ddl.startswith('CREATE TABLE public.test_tbl')
    assert 'id BIGINT' in ddl
    assert 'name TEXT' in ddl
    assert 'amount NUMERIC' in ddl


def test_create_table_no_double_quotes_on_columns():
    """Column names must NOT be double-quoted to match _bulk_load's unquoted INSERT."""
    conn = _make_conn('postgresql')
    step = DataLoadStep(name='t', config={})
    columns = ['subscriber_id', 'plan', 'monthly_amount']
    rows = [('S001', 'premium', 99.99)]
    step._create_table(conn, 'public.tbl', columns, rows)
    ddl = conn.execute_write.call_args[0][0]
    assert '"' not in ddl, f"Found double-quotes in DDL: {ddl}"


def test_create_table_oracle_types():
    conn = _make_conn('oracle')
    step = DataLoadStep(name='t', config={})
    columns = ['id', 'label', 'score']
    rows = [(10, 'A', 3.14)]
    step._create_table(conn, 'MYSCHEMA.SCORES', columns, rows)
    ddl = conn.execute_write.call_args[0][0]
    assert 'id NUMBER(18)' in ddl
    assert 'label VARCHAR2(4000)' in ddl
    assert 'score NUMBER' in ddl


def test_create_table_samples_max_1000_rows():
    """_create_table should sample at most 1000 rows for type inference."""
    conn = _make_conn('postgresql')
    step = DataLoadStep(name='t', config={})
    columns = ['val']
    # Pass 2000 rows; type should be inferred from first 1000 only (all ints)
    rows = [(i,) for i in range(2000)]
    step._create_table(conn, 'public.large', columns, rows)
    ddl = conn.execute_write.call_args[0][0]
    assert 'val BIGINT' in ddl


# ─────────────────────────────────────────────────────────────────────────────
# create_if_missing end-to-end (mocked connection factory)
# ─────────────────────────────────────────────────────────────────────────────

def _make_step(create_if_missing=True, mode='append'):
    return DataLoadStep(name='load_step', config={
        'target_connection_id': 'fake-uuid',
        'target_table': 'public.auto_tbl',
        'mode': mode,
        'create_if_missing': create_if_missing,
        'source': {
            'type': 'file',
            'file_path': '/fake/path.csv',
        },
    })


def _mock_conn(db_type='postgresql', table_exists=False):
    conn = MagicMock()
    conn.db_type = db_type
    conn.__enter__ = lambda s: s
    conn.__exit__ = MagicMock(return_value=False)
    # catalog check: return row if exists
    conn.execute_query.return_value = [(1,)] if table_exists else []
    conn.make_placeholders.return_value = '%s, %s'
    conn.execute_many.return_value = 2
    return conn


@patch('flowforge.steps.data_load.DataLoadStep._load_source')
@patch('flowforge.connections.factory.get_connection')
def test_create_if_missing_creates_when_absent(mock_get_conn, mock_load_source):
    mock_load_source.return_value = (['id', 'name'], [(1, 'Alice'), (2, 'Bob')])
    conn = _mock_conn(table_exists=False)
    mock_get_conn.return_value = conn

    step = _make_step(create_if_missing=True)
    result = step.run({})

    assert result.success is True
    # execute_write should have been called for CREATE TABLE (and no TRUNCATE for append)
    write_calls = [c[0][0] for c in conn.execute_write.call_args_list]
    assert any(c.startswith('CREATE TABLE') for c in write_calls), write_calls
    assert result.logs and 'auto-created' in result.logs


@patch('flowforge.steps.data_load.DataLoadStep._load_source')
@patch('flowforge.connections.factory.get_connection')
def test_create_if_missing_skips_create_when_present(mock_get_conn, mock_load_source):
    mock_load_source.return_value = (['id', 'name'], [(1, 'Alice'), (2, 'Bob')])
    conn = _mock_conn(table_exists=True)
    mock_get_conn.return_value = conn

    step = _make_step(create_if_missing=True, mode='append')
    result = step.run({})

    assert result.success is True
    write_calls = [c[0][0] for c in conn.execute_write.call_args_list]
    assert not any(c.startswith('CREATE TABLE') for c in write_calls), write_calls


@patch('flowforge.steps.data_load.DataLoadStep._load_source')
@patch('flowforge.connections.factory.get_connection')
def test_create_if_missing_false_no_catalog_check(mock_get_conn, mock_load_source):
    mock_load_source.return_value = (['id', 'name'], [(1, 'Alice')])
    conn = _mock_conn(table_exists=False)
    mock_get_conn.return_value = conn

    step = _make_step(create_if_missing=False)
    _ = step.run({})

    # execute_query (catalog check) should not have been called
    conn.execute_query.assert_not_called()


@patch('flowforge.steps.data_load.DataLoadStep._load_source')
@patch('flowforge.connections.factory.get_connection')
def test_replace_mode_truncates_even_after_create(mock_get_conn, mock_load_source):
    """In replace mode, TRUNCATE runs after the table is created."""
    mock_load_source.return_value = (['id'], [(1,), (2,)])
    conn = _mock_conn(table_exists=False)
    mock_get_conn.return_value = conn

    step = _make_step(create_if_missing=True, mode='replace')
    result = step.run({})

    assert result.success is True
    write_calls = [c[0][0] for c in conn.execute_write.call_args_list]
    assert any(c.startswith('CREATE TABLE') for c in write_calls)
    assert any(c.startswith('TRUNCATE') for c in write_calls)
