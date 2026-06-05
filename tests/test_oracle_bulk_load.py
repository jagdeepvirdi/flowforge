"""Tests for Oracle-specific bulk_load paths and shared helpers.

Covers:
  - _parse_sqlldr_counts
  - _read_bad_file
  - _open_raw_connection (Oracle + unsupported db_type)
  - _derive_line_columns
  - _dispatch_single_file routing (oracle+sqlldr, postgresql, fallback)
  - _load_sqlloader (CTL/par file content, subprocess call, log parsing, bad file)
  - _load_postgres_copy (copy_expert, replace/append mode, rollback on error)
  - _load_python_fallback edge cases (no data rows, chunk failure)
  - BulkLoadStep.run with Oracle sqlldr dispatch
  - BulkLoadStep.run connection-resolution failure
  - BulkLoadStep.run per-file exception path (files_failed counter)
  - _validate_bulk_cfg invalid delimiter branch
  - _derive_csv_columns no-header / empty-rows branch
"""
import csv
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ─── CSV helpers ──────────────────────────────────────────────────────────────

def _write_csv(path: Path, rows, header=None):
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        if header:
            w.writerow(header)
        w.writerows(rows)


def _base_cfg(src_dir: str, target: str = 'my_tbl') -> dict:
    return {
        'connection_id':       'conn-uuid',
        'source_directory':    src_dir,
        'target_table':        target,
        'file_type':           'csv',
        'delimiter':           ',',
        'header_rows':         1,
        'footer_rows':         0,
        'load_mode':           'append',
        'column_mapping':      [],
        'use_sqlloader':       False,
        'archive_directory':   '',
        'on_no_files':         'skip',
    }


def _oracle_conn_cfg(**kw) -> dict:
    cfg = {'_db_type': 'oracle', 'username': 'usr', 'password': 'pwd',
           'host': 'dbhost', 'port': 1521, 'service_name': 'ORCL'}
    cfg.update(kw)
    return cfg


def _pg_conn_cfg(**kw) -> dict:
    cfg = {'_db_type': 'postgresql', 'username': 'u', 'password': 'p',
           'host': 'localhost', 'port': 5432, 'database': 'testdb'}
    cfg.update(kw)
    return cfg


def _mock_db_conn():
    conn = MagicMock()
    cur = MagicMock()
    cur.rowcount = -1
    conn.cursor.return_value = cur
    return conn, cur


# ─── _validate_bulk_cfg — invalid delimiter ───────────────────────────────────

def test_invalid_delimiter_quote(tmp_path):
    from flowforge.steps.bulk_load import BulkLoadStep
    cfg = _base_cfg(str(tmp_path))
    cfg['delimiter'] = "'"
    result = BulkLoadStep('bulk', cfg).run({})
    assert result.success is False
    assert 'delimiter' in result.error


def test_invalid_delimiter_two_chars(tmp_path):
    from flowforge.steps.bulk_load import BulkLoadStep
    cfg = _base_cfg(str(tmp_path))
    cfg['delimiter'] = ',,'
    result = BulkLoadStep('bulk', cfg).run({})
    assert result.success is False
    assert 'delimiter' in result.error


def test_invalid_delimiter_backslash(tmp_path):
    from flowforge.steps.bulk_load import BulkLoadStep
    cfg = _base_cfg(str(tmp_path))
    cfg['delimiter'] = '\\'
    result = BulkLoadStep('bulk', cfg).run({})
    assert result.success is False


# ─── _derive_csv_columns — no-header / empty-rows branch ─────────────────────

def test_derive_csv_columns_no_header():
    from flowforge.steps.bulk_load import _derive_csv_columns
    result = _derive_csv_columns([['a', 'b'], ['1', '2']], header_rows=0, col_map={})
    assert result == []


def test_derive_csv_columns_empty_rows():
    from flowforge.steps.bulk_load import _derive_csv_columns
    result = _derive_csv_columns([], header_rows=1, col_map={})
    assert result == []


def test_derive_csv_columns_with_header():
    from flowforge.steps.bulk_load import _derive_csv_columns
    result = _derive_csv_columns([['id', 'name'], ['1', 'Alice']], header_rows=1, col_map={})
    assert result == ['id', 'name']


def test_derive_csv_columns_applies_col_map():
    from flowforge.steps.bulk_load import _derive_csv_columns
    result = _derive_csv_columns(
        [['FIRST_NAME', 'AGE'], ['Alice', '30']],
        header_rows=1,
        col_map={'FIRST_NAME': 'first_name', 'AGE': 'age'},
    )
    assert result == ['first_name', 'age']


# ─── _derive_line_columns ─────────────────────────────────────────────────────

def test_derive_line_columns_no_header():
    from flowforge.steps.bulk_load import _derive_line_columns
    result = _derive_line_columns(['id,name\n', '1,Alice\n'], header_rows=0, col_map={}, delimiter=',')
    assert result is None


def test_derive_line_columns_empty_lines():
    from flowforge.steps.bulk_load import _derive_line_columns
    result = _derive_line_columns([], header_rows=1, col_map={}, delimiter=',')
    assert result is None


def test_derive_line_columns_with_header():
    from flowforge.steps.bulk_load import _derive_line_columns
    result = _derive_line_columns(['id,name\n', '1,Alice\n'], header_rows=1, col_map={}, delimiter=',')
    assert result == ['id', 'name']


def test_derive_line_columns_applies_col_map():
    from flowforge.steps.bulk_load import _derive_line_columns
    result = _derive_line_columns(
        ['FIRST_NAME,AGE\n', 'Alice,30\n'],
        header_rows=1,
        col_map={'FIRST_NAME': 'first_name', 'AGE': 'age'},
        delimiter=',',
    )
    assert result == ['first_name', 'age']


def test_derive_line_columns_strips_whitespace():
    from flowforge.steps.bulk_load import _derive_line_columns
    result = _derive_line_columns([' id , name \n'], header_rows=1, col_map={}, delimiter=',')
    assert result == ['id', 'name']


# ─── _parse_sqlldr_counts ─────────────────────────────────────────────────────

def test_parse_sqlldr_counts_empty():
    from flowforge.steps.bulk_load import _parse_sqlldr_counts
    loaded, failed = _parse_sqlldr_counts('')
    assert loaded == 0
    assert failed == 0


def test_parse_sqlldr_counts_single_loaded():
    from flowforge.steps.bulk_load import _parse_sqlldr_counts
    log = '1 row successfully loaded.'
    loaded, failed = _parse_sqlldr_counts(log)
    assert loaded == 1
    assert failed == 0


def test_parse_sqlldr_counts_plural_loaded():
    from flowforge.steps.bulk_load import _parse_sqlldr_counts
    log = '500 rows successfully loaded.'
    loaded, failed = _parse_sqlldr_counts(log)
    assert loaded == 500


def test_parse_sqlldr_counts_failed_rows():
    from flowforge.steps.bulk_load import _parse_sqlldr_counts
    log = '3 rows not loaded due to data errors.'
    loaded, failed = _parse_sqlldr_counts(log)
    assert loaded == 0
    assert failed == 3


def test_parse_sqlldr_counts_both_loaded_and_failed():
    from flowforge.steps.bulk_load import _parse_sqlldr_counts
    log = (
        'Table MY_TABLE, loaded from every logical record.\n'
        '10 rows successfully loaded.\n'
        '2 rows not loaded due to data errors.\n'
    )
    loaded, failed = _parse_sqlldr_counts(log)
    assert loaded == 10
    assert failed == 2


def test_parse_sqlldr_counts_no_match():
    from flowforge.steps.bulk_load import _parse_sqlldr_counts
    log = 'SQL*Loader: Release 19.0.0.0.0\nCopyright (c) 1982, 2019, Oracle.'
    loaded, failed = _parse_sqlldr_counts(log)
    assert loaded == 0
    assert failed == 0


# ─── _read_bad_file ───────────────────────────────────────────────────────────

def test_read_bad_file_nonexistent(tmp_path):
    from flowforge.steps.bulk_load import _read_bad_file
    result = _read_bad_file(tmp_path / 'load.bad')
    assert result == ''


def test_read_bad_file_empty(tmp_path):
    from flowforge.steps.bulk_load import _read_bad_file
    f = tmp_path / 'load.bad'
    f.write_text('')
    result = _read_bad_file(f)
    assert result == ''


def test_read_bad_file_with_content(tmp_path):
    from flowforge.steps.bulk_load import _read_bad_file
    f = tmp_path / 'load.bad'
    f.write_text('bad_col_1,bad_col_2\nrejected_row_1,value\n')
    result = _read_bad_file(f)
    assert 'Rejected rows' in result
    assert 'bad_col_1' in result


def test_read_bad_file_limits_to_50_lines(tmp_path):
    from flowforge.steps.bulk_load import _read_bad_file
    f = tmp_path / 'load.bad'
    f.write_text('\n'.join(f'row{i}' for i in range(100)))
    result = _read_bad_file(f)
    lines = result.splitlines()
    # header line + up to 50 content lines
    assert len(lines) <= 52


# ─── _open_raw_connection — Oracle path ──────────────────────────────────────

def test_open_raw_conn_oracle_calls_connect():
    from flowforge.steps.bulk_load import _open_raw_connection
    fake_oracledb = MagicMock()
    conn_cfg = _oracle_conn_cfg()
    with patch.dict(sys.modules, {'oracledb': fake_oracledb}):
        _open_raw_connection(conn_cfg)
    fake_oracledb.connect.assert_called_once_with(
        user='usr', password='pwd', dsn='dbhost:1521/ORCL'
    )


def test_open_raw_conn_oracle_uses_service_name():
    from flowforge.steps.bulk_load import _open_raw_connection
    fake_oracledb = MagicMock()
    conn_cfg = _oracle_conn_cfg(service_name='MYPDB', database='ignored')
    with patch.dict(sys.modules, {'oracledb': fake_oracledb}):
        _open_raw_connection(conn_cfg)
    dsn_used = fake_oracledb.connect.call_args.kwargs['dsn']
    assert 'MYPDB' in dsn_used
    assert 'ignored' not in dsn_used


def test_open_raw_conn_oracle_falls_back_to_database():
    from flowforge.steps.bulk_load import _open_raw_connection
    fake_oracledb = MagicMock()
    conn_cfg = _oracle_conn_cfg()
    del conn_cfg['service_name']
    conn_cfg['database'] = 'FALLBACKSVC'
    with patch.dict(sys.modules, {'oracledb': fake_oracledb}):
        _open_raw_connection(conn_cfg)
    dsn_used = fake_oracledb.connect.call_args.kwargs['dsn']
    assert 'FALLBACKSVC' in dsn_used


def test_open_raw_conn_unsupported_db_type_raises():
    from flowforge.steps.bulk_load import _open_raw_connection
    with pytest.raises(ValueError, match='Unsupported db_type'):
        _open_raw_connection({'_db_type': 'mongodb'})


# ─── _dispatch_single_file routing ───────────────────────────────────────────

def test_dispatch_oracle_sqlloader_calls_load_sqlloader(tmp_path):
    from flowforge.steps.bulk_load import _dispatch_single_file
    f = tmp_path / 'data.csv'
    f.write_text('id,name\n1,A\n')
    with patch('flowforge.steps.bulk_load._load_sqlloader',
               return_value=(1, 0, 'ok')) as mock:
        _dispatch_single_file('oracle', True, _oracle_conn_cfg(), f,
                              ',', 1, 0, 'tbl', 'append', [])
    mock.assert_called_once()


def test_dispatch_oracle_no_sqlloader_calls_python_fallback(tmp_path):
    from flowforge.steps.bulk_load import _dispatch_single_file
    f = tmp_path / 'data.csv'
    f.write_text('id,name\n1,A\n')
    with patch('flowforge.steps.bulk_load._load_python_fallback',
               return_value=(1, 0, 'ok')) as mock:
        _dispatch_single_file('oracle', False, _oracle_conn_cfg(), f,
                              ',', 1, 0, 'tbl', 'append', [])
    mock.assert_called_once()


def test_dispatch_postgresql_calls_postgres_copy(tmp_path):
    from flowforge.steps.bulk_load import _dispatch_single_file
    f = tmp_path / 'data.csv'
    f.write_text('id,name\n1,A\n')
    with patch('flowforge.steps.bulk_load._load_postgres_copy',
               return_value=(1, 0, 'ok')) as mock:
        _dispatch_single_file('postgresql', False, _pg_conn_cfg(), f,
                              ',', 1, 0, 'tbl', 'append', [])
    mock.assert_called_once()


def test_dispatch_other_db_type_calls_python_fallback(tmp_path):
    from flowforge.steps.bulk_load import _dispatch_single_file
    f = tmp_path / 'data.csv'
    f.write_text('id,name\n1,A\n')
    with patch('flowforge.steps.bulk_load._load_python_fallback',
               return_value=(1, 0, 'ok')) as mock:
        _dispatch_single_file('mysql', False, {'_db_type': 'mysql'}, f,
                              ',', 1, 0, 'tbl', 'append', [])
    mock.assert_called_once()


# ─── _load_sqlloader ─────────────────────────────────────────────────────────

def test_sqlldr_ctl_append_mode(tmp_path):
    from flowforge.steps.bulk_load import _load_sqlloader
    csv_file = tmp_path / 'src.csv'
    csv_file.write_text('col_a,col_b\n1,Alice\n2,Bob\n')
    wd = str(tmp_path / 'wd')
    Path(wd).mkdir()
    with patch('tempfile.mkdtemp', return_value=wd), \
         patch('shutil.rmtree'), \
         patch('subprocess.run'):
        _load_sqlloader(_oracle_conn_cfg(), csv_file, ',', 1, 0, 'my_tbl', 'append', [])
    ctl = (Path(wd) / 'load.ctl').read_text()
    assert 'APPEND' in ctl
    assert 'TRUNCATE' not in ctl


def test_sqlldr_ctl_truncate_mode_for_replace(tmp_path):
    from flowforge.steps.bulk_load import _load_sqlloader
    csv_file = tmp_path / 'src.csv'
    csv_file.write_text('col_a,col_b\n1,Alice\n')
    wd = str(tmp_path / 'wd')
    Path(wd).mkdir()
    with patch('tempfile.mkdtemp', return_value=wd), \
         patch('shutil.rmtree'), \
         patch('subprocess.run'):
        _load_sqlloader(_oracle_conn_cfg(), csv_file, ',', 1, 0, 'my_tbl', 'replace', [])
    ctl = (Path(wd) / 'load.ctl').read_text()
    assert 'TRUNCATE' in ctl
    assert 'APPEND' not in ctl


def test_sqlldr_ctl_contains_table_name(tmp_path):
    from flowforge.steps.bulk_load import _load_sqlloader
    csv_file = tmp_path / 'src.csv'
    csv_file.write_text('id,name\n1,Alice\n')
    wd = str(tmp_path / 'wd')
    Path(wd).mkdir()
    with patch('tempfile.mkdtemp', return_value=wd), \
         patch('shutil.rmtree'), \
         patch('subprocess.run'):
        _load_sqlloader(_oracle_conn_cfg(), csv_file, ',', 1, 0, 'schema.MY_TABLE', 'append', [])
    ctl = (Path(wd) / 'load.ctl').read_text()
    assert 'schema.MY_TABLE' in ctl


def test_sqlldr_ctl_contains_column_names(tmp_path):
    from flowforge.steps.bulk_load import _load_sqlloader
    csv_file = tmp_path / 'src.csv'
    csv_file.write_text('emp_id,emp_name,dept\n1,Alice,Eng\n')
    wd = str(tmp_path / 'wd')
    Path(wd).mkdir()
    with patch('tempfile.mkdtemp', return_value=wd), \
         patch('shutil.rmtree'), \
         patch('subprocess.run'):
        _load_sqlloader(_oracle_conn_cfg(), csv_file, ',', 1, 0, 'tbl', 'append', [])
    ctl = (Path(wd) / 'load.ctl').read_text()
    assert 'emp_id' in ctl
    assert 'emp_name' in ctl
    assert 'dept' in ctl


def test_sqlldr_ctl_contains_delimiter(tmp_path):
    from flowforge.steps.bulk_load import _load_sqlloader
    csv_file = tmp_path / 'src.csv'
    csv_file.write_text('id|name\n1|Alice\n')
    wd = str(tmp_path / 'wd')
    Path(wd).mkdir()
    with patch('tempfile.mkdtemp', return_value=wd), \
         patch('shutil.rmtree'), \
         patch('subprocess.run'):
        _load_sqlloader(_oracle_conn_cfg(), csv_file, '|', 1, 0, 'tbl', 'append', [])
    ctl = (Path(wd) / 'load.ctl').read_text()
    assert '|' in ctl


def test_sqlldr_par_file_contains_credentials(tmp_path):
    from flowforge.steps.bulk_load import _load_sqlloader
    csv_file = tmp_path / 'src.csv'
    csv_file.write_text('id,name\n1,Alice\n')
    wd = str(tmp_path / 'wd')
    Path(wd).mkdir()
    with patch('tempfile.mkdtemp', return_value=wd), \
         patch('shutil.rmtree'), \
         patch('subprocess.run'):
        _load_sqlloader(_oracle_conn_cfg(), csv_file, ',', 1, 0, 'tbl', 'append', [])
    par = (Path(wd) / 'load.par').read_text()
    assert 'usr' in par
    assert 'pwd' in par
    assert 'dbhost' in par
    assert 'ORCL' in par


def test_sqlldr_par_file_references_ctl_and_log(tmp_path):
    from flowforge.steps.bulk_load import _load_sqlloader
    csv_file = tmp_path / 'src.csv'
    csv_file.write_text('id,name\n1,A\n')
    wd = str(tmp_path / 'wd')
    Path(wd).mkdir()
    with patch('tempfile.mkdtemp', return_value=wd), \
         patch('shutil.rmtree'), \
         patch('subprocess.run'):
        _load_sqlloader(_oracle_conn_cfg(), csv_file, ',', 1, 0, 'tbl', 'append', [])
    par = (Path(wd) / 'load.par').read_text()
    assert 'load.ctl' in par
    assert 'load.log' in par
    assert 'load.bad' in par


def test_sqlldr_subprocess_called_with_sqlldr(tmp_path):
    from flowforge.steps.bulk_load import _load_sqlloader
    csv_file = tmp_path / 'src.csv'
    csv_file.write_text('id,name\n1,A\n')
    with patch('subprocess.run') as mock_run, \
         patch('shutil.rmtree'):
        _load_sqlloader(_oracle_conn_cfg(), csv_file, ',', 1, 0, 'tbl', 'append', [])
    cmd = mock_run.call_args[0][0]
    assert cmd[0] == 'sqlldr'
    assert any('parfile=' in arg for arg in cmd)


def test_sqlldr_tmpdir_cleaned_up(tmp_path):
    from flowforge.steps.bulk_load import _load_sqlloader
    csv_file = tmp_path / 'src.csv'
    csv_file.write_text('id,name\n1,A\n')
    wd = str(tmp_path / 'wd')
    Path(wd).mkdir()
    with patch('tempfile.mkdtemp', return_value=wd), \
         patch('shutil.rmtree') as mock_rmtree, \
         patch('subprocess.run'):
        _load_sqlloader(_oracle_conn_cfg(), csv_file, ',', 1, 0, 'tbl', 'append', [])
    # _load_sqlloader wraps the mkdtemp result in Path(), so rmtree receives a Path object
    mock_rmtree.assert_called_once_with(Path(wd), ignore_errors=True)


def test_sqlldr_parses_log_for_counts(tmp_path):
    from flowforge.steps.bulk_load import _load_sqlloader
    csv_file = tmp_path / 'src.csv'
    csv_file.write_text('id,name\n1,A\n2,B\n3,C\n')
    wd = str(tmp_path / 'wd')
    Path(wd).mkdir()

    def _write_log(*args, **kwargs):
        # _parse_sqlldr_counts matches 'rows' (plural) only — use plural form
        (Path(wd) / 'load.log').write_text(
            '3 rows successfully loaded.\n2 rows not loaded due to data errors.\n'
        )

    with patch('tempfile.mkdtemp', return_value=wd), \
         patch('shutil.rmtree'), \
         patch('subprocess.run', side_effect=_write_log):
        loaded, failed, summary = _load_sqlloader(
            _oracle_conn_cfg(), csv_file, ',', 1, 0, 'tbl', 'append', []
        )
    assert loaded == 3
    assert failed == 2


def test_sqlldr_handles_missing_log_file(tmp_path):
    from flowforge.steps.bulk_load import _load_sqlloader
    csv_file = tmp_path / 'src.csv'
    csv_file.write_text('id,name\n1,A\n')
    with patch('subprocess.run'), patch('shutil.rmtree'):
        loaded, failed, summary = _load_sqlloader(
            _oracle_conn_cfg(), csv_file, ',', 1, 0, 'tbl', 'append', []
        )
    assert loaded == 0
    assert failed == 0
    assert isinstance(summary, str)


def test_sqlldr_includes_bad_file_in_summary(tmp_path):
    from flowforge.steps.bulk_load import _load_sqlloader
    csv_file = tmp_path / 'src.csv'
    csv_file.write_text('id,name\n1,A\n')
    wd = str(tmp_path / 'wd')
    Path(wd).mkdir()

    def _write_bad(*args, **kwargs):
        (Path(wd) / 'load.bad').write_text('bad_row,bad_col\n')

    with patch('tempfile.mkdtemp', return_value=wd), \
         patch('shutil.rmtree'), \
         patch('subprocess.run', side_effect=_write_bad):
        _, _, summary = _load_sqlloader(
            _oracle_conn_cfg(), csv_file, ',', 1, 0, 'tbl', 'append', []
        )
    assert 'Rejected rows' in summary


def test_sqlldr_applies_column_mapping(tmp_path):
    from flowforge.steps.bulk_load import _load_sqlloader
    csv_file = tmp_path / 'src.csv'
    csv_file.write_text('FIRST_NAME,AGE\nAlice,30\n')
    wd = str(tmp_path / 'wd')
    Path(wd).mkdir()
    col_map = [{'source': 'FIRST_NAME', 'target': 'first_name'},
               {'source': 'AGE', 'target': 'age'}]
    with patch('tempfile.mkdtemp', return_value=wd), \
         patch('shutil.rmtree'), \
         patch('subprocess.run'):
        _load_sqlloader(_oracle_conn_cfg(), csv_file, ',', 1, 0, 'tbl', 'append', col_map)
    ctl = (Path(wd) / 'load.ctl').read_text()
    assert 'first_name' in ctl
    assert 'age' in ctl
    assert 'FIRST_NAME' not in ctl


# ─── _load_postgres_copy ─────────────────────────────────────────────────────

def test_postgres_copy_calls_copy_expert(tmp_path):
    from flowforge.steps.bulk_load import _load_postgres_copy
    csv_file = tmp_path / 'data.csv'
    csv_file.write_text('id,name\n1,Alice\n2,Bob\n')
    conn, cur = _mock_db_conn()
    cur.rowcount = 2
    with patch('flowforge.steps.bulk_load._open_raw_connection', return_value=conn):
        loaded, failed, summary = _load_postgres_copy(
            _pg_conn_cfg(), csv_file, ',', 1, 0, 'my_tbl', 'append', []
        )
    cur.copy_expert.assert_called_once()
    assert loaded == 2
    assert failed == 0


def test_postgres_copy_sql_contains_table_name(tmp_path):
    from flowforge.steps.bulk_load import _load_postgres_copy
    csv_file = tmp_path / 'data.csv'
    csv_file.write_text('id,name\n1,Alice\n')
    conn, cur = _mock_db_conn()
    cur.rowcount = 1
    with patch('flowforge.steps.bulk_load._open_raw_connection', return_value=conn):
        _load_postgres_copy(_pg_conn_cfg(), csv_file, ',', 1, 0, 'sales.orders', 'append', [])
    copy_sql = cur.copy_expert.call_args[0][0]
    assert 'sales.orders' in copy_sql


def test_postgres_copy_replace_mode_truncates(tmp_path):
    from flowforge.steps.bulk_load import _load_postgres_copy
    csv_file = tmp_path / 'data.csv'
    csv_file.write_text('id,name\n1,Alice\n')
    conn, cur = _mock_db_conn()
    cur.rowcount = 1
    with patch('flowforge.steps.bulk_load._open_raw_connection', return_value=conn):
        _load_postgres_copy(_pg_conn_cfg(), csv_file, ',', 1, 0, 'my_tbl', 'replace', [])
    execute_sqls = [c[0][0] for c in cur.execute.call_args_list]
    assert any('TRUNCATE' in sql for sql in execute_sqls)


def test_postgres_copy_append_mode_no_truncate(tmp_path):
    from flowforge.steps.bulk_load import _load_postgres_copy
    csv_file = tmp_path / 'data.csv'
    csv_file.write_text('id,name\n1,Alice\n')
    conn, cur = _mock_db_conn()
    cur.rowcount = 1
    with patch('flowforge.steps.bulk_load._open_raw_connection', return_value=conn):
        _load_postgres_copy(_pg_conn_cfg(), csv_file, ',', 1, 0, 'my_tbl', 'append', [])
    execute_sqls = [c[0][0] for c in cur.execute.call_args_list]
    assert not any('TRUNCATE' in sql for sql in execute_sqls)


def test_postgres_copy_col_clause_with_header(tmp_path):
    from flowforge.steps.bulk_load import _load_postgres_copy
    csv_file = tmp_path / 'data.csv'
    csv_file.write_text('emp_id,emp_name\n1,Alice\n')
    conn, cur = _mock_db_conn()
    cur.rowcount = 1
    with patch('flowforge.steps.bulk_load._open_raw_connection', return_value=conn):
        _load_postgres_copy(_pg_conn_cfg(), csv_file, ',', 1, 0, 'tbl', 'append', [])
    copy_sql = cur.copy_expert.call_args[0][0]
    assert 'emp_id' in copy_sql
    assert 'emp_name' in copy_sql


def test_postgres_copy_no_col_clause_without_header(tmp_path):
    from flowforge.steps.bulk_load import _load_postgres_copy
    csv_file = tmp_path / 'data.csv'
    csv_file.write_text('1,Alice\n2,Bob\n')
    conn, cur = _mock_db_conn()
    cur.rowcount = 2
    with patch('flowforge.steps.bulk_load._open_raw_connection', return_value=conn):
        _load_postgres_copy(_pg_conn_cfg(), csv_file, ',', 0, 0, 'tbl', 'append', [])
    copy_sql = cur.copy_expert.call_args[0][0]
    # No column list clause — just COPY tbl FROM STDIN
    assert 'tbl FROM STDIN' in copy_sql or '()' not in copy_sql


def test_postgres_copy_negative_rowcount_falls_back_to_line_count(tmp_path):
    from flowforge.steps.bulk_load import _load_postgres_copy
    csv_file = tmp_path / 'data.csv'
    csv_file.write_text('id,name\n1,Alice\n2,Bob\n3,Carol\n')
    conn, cur = _mock_db_conn()
    cur.rowcount = -1  # driver returns -1 when unknown
    with patch('flowforge.steps.bulk_load._open_raw_connection', return_value=conn):
        loaded, _, _ = _load_postgres_copy(_pg_conn_cfg(), csv_file, ',', 1, 0, 'tbl', 'append', [])
    assert loaded == 3  # 3 data lines after stripping header


def test_postgres_copy_rollback_on_exception(tmp_path):
    from flowforge.steps.bulk_load import _load_postgres_copy
    csv_file = tmp_path / 'data.csv'
    csv_file.write_text('id,name\n1,Alice\n')
    conn, cur = _mock_db_conn()
    cur.copy_expert.side_effect = Exception('copy failed')
    with patch('flowforge.steps.bulk_load._open_raw_connection', return_value=conn):
        with pytest.raises(Exception, match='copy failed'):
            _load_postgres_copy(_pg_conn_cfg(), csv_file, ',', 1, 0, 'tbl', 'append', [])
    conn.rollback.assert_called_once()


def test_postgres_copy_closes_connection_on_exception(tmp_path):
    from flowforge.steps.bulk_load import _load_postgres_copy
    csv_file = tmp_path / 'data.csv'
    csv_file.write_text('id,name\n1,Alice\n')
    conn, cur = _mock_db_conn()
    cur.copy_expert.side_effect = Exception('copy failed')
    with patch('flowforge.steps.bulk_load._open_raw_connection', return_value=conn):
        with pytest.raises(Exception):
            _load_postgres_copy(_pg_conn_cfg(), csv_file, ',', 1, 0, 'tbl', 'append', [])
    conn.close.assert_called_once()


# ─── _load_python_fallback edge cases ────────────────────────────────────────

def test_python_fallback_no_data_rows_returns_zero(tmp_path):
    """CSV with only a header and no data rows returns (0, 0, ...) without DB calls."""
    from flowforge.steps.bulk_load import _load_python_fallback
    csv_file = tmp_path / 'empty.csv'
    csv_file.write_text('id,name\n')  # header only
    conn, cur = _mock_db_conn()
    with patch('flowforge.steps.bulk_load._open_raw_connection', return_value=conn):
        loaded, failed, msg = _load_python_fallback(
            {'_db_type': 'other'}, csv_file, ',', 1, 0, 'tbl', 'append', []
        )
    assert loaded == 0
    assert failed == 0
    assert 'No data rows' in msg
    cur.executemany.assert_not_called()


def test_python_fallback_chunk_failure_increments_failed(tmp_path):
    from flowforge.steps.bulk_load import _load_python_fallback
    csv_file = tmp_path / 'data.csv'
    csv_file.write_text('id,name\n1,Alice\n2,Bob\n')
    conn, cur = _mock_db_conn()
    cur.executemany.side_effect = Exception('constraint violation')
    with patch('flowforge.steps.bulk_load._open_raw_connection', return_value=conn):
        loaded, failed, summary = _load_python_fallback(
            {'_db_type': 'other'}, csv_file, ',', 1, 0, 'tbl', 'append', []
        )
    assert failed == 2  # both rows in the failed chunk
    assert loaded == 0
    conn.rollback.assert_called()


def test_python_fallback_chunk_failure_logs_error(tmp_path):
    from flowforge.steps.bulk_load import _load_python_fallback
    csv_file = tmp_path / 'data.csv'
    csv_file.write_text('id,name\n1,Alice\n')
    conn, cur = _mock_db_conn()
    cur.executemany.side_effect = Exception('FK violation')
    with patch('flowforge.steps.bulk_load._open_raw_connection', return_value=conn):
        _, _, summary = _load_python_fallback(
            {'_db_type': 'other'}, csv_file, ',', 1, 0, 'tbl', 'append', []
        )
    assert 'failed' in summary.lower() or 'Chunk' in summary


def test_python_fallback_oracle_uses_oracledb_connect(tmp_path):
    """Python fallback calls oracledb.connect() when db_type=oracle."""
    from flowforge.steps.bulk_load import _load_python_fallback
    csv_file = tmp_path / 'data.csv'
    csv_file.write_text('id,name\n1,Alice\n')
    fake_oracledb = MagicMock()
    fake_conn = MagicMock()
    fake_cur = MagicMock()
    fake_cur.rowcount = 1
    fake_conn.cursor.return_value = fake_cur
    fake_oracledb.connect.return_value = fake_conn
    with patch.dict(sys.modules, {'oracledb': fake_oracledb}):
        _load_python_fallback(
            _oracle_conn_cfg(), csv_file, ',', 1, 0, 'tbl', 'append', []
        )
    fake_oracledb.connect.assert_called_once()


# ─── BulkLoadStep.run — Oracle sqlldr dispatch (full integration) ─────────────

def test_bulkloadstep_dispatches_to_sqlloader_for_oracle(tmp_path):
    from flowforge.steps.bulk_load import BulkLoadStep
    _write_csv(tmp_path / 'data.csv', [['1', 'Alice']], header=['id', 'name'])
    cfg = _base_cfg(str(tmp_path))
    cfg['use_sqlloader'] = True

    with patch('flowforge.steps.bulk_load._resolve_connection',
               return_value=_oracle_conn_cfg()), \
         patch('flowforge.steps.bulk_load._load_sqlloader',
               return_value=(5, 0, 'SQL*Loader: 5 loaded')) as mock_sqlldr:
        result = BulkLoadStep('bulk', cfg).run({})

    mock_sqlldr.assert_called_once()
    assert result.success is True
    assert result.records_loaded == 5


def test_bulkloadstep_oracle_no_sqlldr_uses_python_fallback(tmp_path):
    from flowforge.steps.bulk_load import BulkLoadStep
    _write_csv(tmp_path / 'data.csv', [['1', 'Alice']], header=['id', 'name'])
    cfg = _base_cfg(str(tmp_path))
    cfg['use_sqlloader'] = False

    with patch('flowforge.steps.bulk_load._resolve_connection',
               return_value=_oracle_conn_cfg()), \
         patch('flowforge.steps.bulk_load._load_python_fallback',
               return_value=(1, 0, 'Python fallback: 1 loaded')) as mock_fb:
        result = BulkLoadStep('bulk', cfg).run({})

    mock_fb.assert_called_once()
    assert result.success is True


# ─── BulkLoadStep.run — connection-resolution failure ────────────────────────

def test_bulkloadstep_connection_resolution_failure(tmp_path):
    from flowforge.steps.bulk_load import BulkLoadStep
    _write_csv(tmp_path / 'data.csv', [['1', 'A']], header=['id', 'v'])
    cfg = _base_cfg(str(tmp_path))
    with patch('flowforge.steps.bulk_load._resolve_connection',
               side_effect=ValueError('connection not found')):
        result = BulkLoadStep('bulk', cfg).run({})
    assert result.success is False
    assert 'could not open connection' in result.error


# ─── BulkLoadStep.run — per-file exception (files_failed counter) ─────────────

def test_bulkloadstep_per_file_exception_increments_files_failed(tmp_path):
    from flowforge.steps.bulk_load import BulkLoadStep
    _write_csv(tmp_path / 'good.csv', [['1', 'A']], header=['id', 'v'])
    _write_csv(tmp_path / 'bad.csv',  [['2', 'B']], header=['id', 'v'])
    cfg = _base_cfg(str(tmp_path))

    call_count = {'n': 0}

    def _dispatch_side_effect(*args, **kwargs):
        call_count['n'] += 1
        if call_count['n'] == 1:
            raise RuntimeError('simulated load error')
        return 1, 0, 'ok'

    with patch('flowforge.steps.bulk_load._resolve_connection',
               return_value={'_db_type': 'other'}), \
         patch('flowforge.steps.bulk_load._dispatch_single_file',
               side_effect=_dispatch_side_effect):
        result = BulkLoadStep('bulk', cfg).run({})

    assert result.files_found == 2
    assert result.files_failed == 1
    assert result.files_loaded == 1
    assert result.success is False


# ─── _open_raw_connection — PostgreSQL path ───────────────────────────────────

def test_open_raw_conn_postgresql_calls_psycopg2_connect():
    from flowforge.steps.bulk_load import _open_raw_connection
    fake_psycopg2 = MagicMock()
    conn_cfg = _pg_conn_cfg()
    with patch.dict(sys.modules, {'psycopg2': fake_psycopg2}):
        _open_raw_connection(conn_cfg)
    fake_psycopg2.connect.assert_called_once_with(
        host='localhost', port=5432, dbname='testdb', user='u', password='p'
    )


def test_open_raw_conn_postgresql_default_db_type():
    """When _db_type is absent, postgresql is assumed."""
    from flowforge.steps.bulk_load import _open_raw_connection
    fake_psycopg2 = MagicMock()
    conn_cfg = {'host': 'h', 'port': 5432, 'database': 'db', 'username': 'u', 'password': 'p'}
    with patch.dict(sys.modules, {'psycopg2': fake_psycopg2}):
        _open_raw_connection(conn_cfg)
    fake_psycopg2.connect.assert_called_once()


# ─── _load_bulk_load_config — DB model loading ────────────────────────────────
# db is imported lazily inside the function, so patch at the source module.

def test_load_bulk_load_config_not_found_returns_none():
    from flowforge.steps.bulk_load import _load_bulk_load_config
    with patch('flowforge.db.models.db') as mock_db:
        mock_db.session.get.return_value = None
        result = _load_bulk_load_config('nonexistent-uuid')
    assert result is None


def test_load_bulk_load_config_returns_dict():
    from flowforge.steps.bulk_load import _load_bulk_load_config
    row = MagicMock()
    row.connection_id = 'conn-uuid'
    row.source_directory = '/data/in'
    row.file_prefix = 'LOAD_'
    row.file_prefix_exclude = ''
    row.file_type = 'csv'
    row.delimiter = ','
    row.header_rows = 1
    row.footer_rows = 0
    row.target_table = 'my_table'
    row.load_mode = 'append'
    row.column_mapping = []
    row.use_sqlloader = False
    row.archive_directory = '/data/archive'
    row.on_no_files = 'skip'
    with patch('flowforge.db.models.db') as mock_db:
        mock_db.session.get.return_value = row
        result = _load_bulk_load_config('some-uuid')
    assert result['connection_id'] == 'conn-uuid'
    assert result['source_directory'] == '/data/in'
    assert result['target_table'] == 'my_table'
    assert result['use_sqlloader'] is False


def test_load_bulk_load_config_none_fields_default():
    """None DB fields fall back to sensible defaults."""
    from flowforge.steps.bulk_load import _load_bulk_load_config
    row = MagicMock()
    row.connection_id = None
    row.source_directory = None
    row.file_prefix = None
    row.file_prefix_exclude = None
    row.file_type = None
    row.delimiter = None
    row.header_rows = None
    row.footer_rows = None
    row.target_table = None
    row.load_mode = None
    row.column_mapping = None
    row.use_sqlloader = False
    row.archive_directory = None
    row.on_no_files = None
    with patch('flowforge.db.models.db') as mock_db:
        mock_db.session.get.return_value = row
        result = _load_bulk_load_config('uuid')
    assert result['delimiter'] == ','
    assert result['header_rows'] == 1
    assert result['footer_rows'] == 0
    assert result['file_type'] == 'csv'
    assert result['load_mode'] == 'append'
    assert result['on_no_files'] == 'skip'


# ─── _resolve_connection ──────────────────────────────────────────────────────

def test_resolve_connection_not_found_raises():
    from flowforge.steps.bulk_load import _resolve_connection
    with patch('flowforge.db.models.db') as mock_db:
        mock_db.session.get.return_value = None
        with pytest.raises(ValueError, match='DB connection not found'):
            _resolve_connection('nonexistent-uuid')


def test_resolve_connection_returns_decrypted_config():
    from flowforge.steps.bulk_load import _resolve_connection
    row = MagicMock()
    row.db_type = 'oracle'
    row.config = 'encrypted_blob'
    decrypted = {'host': 'dbhost', 'port': 1521, 'username': 'usr', 'password': 'cleartext'}
    with patch('flowforge.db.models.db') as mock_db, \
         patch('flowforge.crypto.decrypt_config', return_value=decrypted) as mock_dec:
        mock_db.session.get.return_value = row
        result = _resolve_connection('some-uuid')
    mock_dec.assert_called_once_with('encrypted_blob')
    assert result['_db_type'] == 'oracle'
    assert result['host'] == 'dbhost'


def test_resolve_connection_injects_db_type():
    from flowforge.steps.bulk_load import _resolve_connection
    row = MagicMock()
    row.db_type = 'postgresql'
    row.config = 'enc'
    with patch('flowforge.db.models.db') as mock_db, \
         patch('flowforge.crypto.decrypt_config', return_value={}):
        mock_db.session.get.return_value = row
        result = _resolve_connection('uuid')
    assert result['_db_type'] == 'postgresql'


# ─── _load_sqlloader — chmod NotImplementedError path (Windows) ───────────────

def test_sqlldr_chmod_not_implemented_is_silenced(tmp_path):
    """par_file.chmod() raising NotImplementedError must be caught silently."""
    from flowforge.steps.bulk_load import _load_sqlloader
    csv_file = tmp_path / 'src.csv'
    csv_file.write_text('id,name\n1,A\n')

    _original_write_text = Path.write_text

    def _chmod_raises(self, mode):
        raise NotImplementedError('chmod not supported')

    with patch.object(Path, 'chmod', _chmod_raises), \
         patch('subprocess.run'), \
         patch('shutil.rmtree'):
        # Must not raise even though chmod raises NotImplementedError
        loaded, failed, summary = _load_sqlloader(
            _oracle_conn_cfg(), csv_file, ',', 1, 0, 'tbl', 'append', []
        )
    assert isinstance(loaded, int)
    assert isinstance(failed, int)
