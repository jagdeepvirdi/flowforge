"""Unit tests for the V2 bulk-load dry-run insert test — the extension to
preview_bulk_load() that actually attempts inserting the sampled rows inside
a transaction (rolled back, never committed) to catch type-coercion and
constraint errors that untyped CSV text can't reveal on its own.

Covers: _classify_insert_error, _dry_run_insert_rows, _group_insert_errors,
_insert_error_summary, and preview_bulk_load(dry_run=True) end-to-end.
"""
import csv
from pathlib import Path
from unittest.mock import MagicMock, patch


def _write_csv(path: Path, rows: list[list[str]], header: list[str] | None = None):
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.writer(fh)
        if header:
            writer.writerow(header)
        writer.writerows(rows)


# ─── _classify_insert_error ─────────────────────────────────────────────────

def test_classify_error_uses_psycopg2_diag_sqlstate_and_column():
    from flowforge.steps.bulk_load import _classify_insert_error

    exc = Exception('null value in column "email" violates not-null constraint')
    exc.diag = MagicMock(sqlstate='23502', column_name='email')
    error_type, column = _classify_insert_error(exc)
    assert error_type == 'not_null_violation'
    assert column == 'email'


def test_classify_error_unique_violation_via_diag():
    from flowforge.steps.bulk_load import _classify_insert_error
    exc = Exception('duplicate key value violates unique constraint')
    exc.diag = MagicMock(sqlstate='23505', column_name=None)
    error_type, column = _classify_insert_error(exc)
    assert error_type == 'unique_violation'
    assert column is None


def test_classify_error_generic_22_sqlstate_is_invalid_type():
    from flowforge.steps.bulk_load import _classify_insert_error
    exc = Exception('invalid input syntax for type integer')
    exc.diag = MagicMock(sqlstate='22P02', column_name='age')
    error_type, column = _classify_insert_error(exc)
    assert error_type == 'invalid_type'
    assert column == 'age'


def test_classify_error_falls_back_to_message_matching_without_diag():
    from flowforge.steps.bulk_load import _classify_insert_error
    error_type, column = _classify_insert_error(Exception('NULL value not allowed for NOT NULL column'))
    assert error_type == 'not_null_violation'
    assert column is None


def test_classify_error_oracle_ora_code_not_null():
    from flowforge.steps.bulk_load import _classify_insert_error
    error_type, _ = _classify_insert_error(Exception('ORA-01400: cannot insert NULL into ("SCHEMA"."T"."EMAIL")'))
    assert error_type == 'not_null_violation'


def test_classify_error_oracle_ora_code_unique():
    from flowforge.steps.bulk_load import _classify_insert_error
    error_type, _ = _classify_insert_error(Exception('ORA-00001: unique constraint violated'))
    assert error_type == 'unique_violation'


def test_classify_error_unknown_defaults_to_db_error():
    from flowforge.steps.bulk_load import _classify_insert_error
    error_type, column = _classify_insert_error(Exception('something completely unexpected happened'))
    assert error_type == 'db_error'
    assert column is None


# ─── _group_insert_errors ────────────────────────────────────────────────────

def test_group_insert_errors_groups_by_column_and_type():
    from flowforge.steps.bulk_load import _group_insert_errors
    row_errors = [
        {'row_index': 0, 'column': 'email', 'error_type': 'not_null_violation', 'message': 'null value'},
        {'row_index': 3, 'column': 'email', 'error_type': 'not_null_violation', 'message': 'null value'},
        {'row_index': 5, 'column': 'id',    'error_type': 'unique_violation',   'message': 'dup'},
    ]
    groups = _group_insert_errors(row_errors)
    assert len(groups) == 2
    email_group = next(g for g in groups if g['column'] == 'email')
    assert email_group['row_indices'] == [0, 3]
    assert email_group['count'] == 2
    assert email_group['error_type'] == 'not_null_violation'


def test_group_insert_errors_sorted_by_count_descending():
    from flowforge.steps.bulk_load import _group_insert_errors
    row_errors = [
        {'row_index': 0, 'column': 'a', 'error_type': 'x', 'message': 'm'},
        {'row_index': 1, 'column': 'b', 'error_type': 'y', 'message': 'm'},
        {'row_index': 2, 'column': 'b', 'error_type': 'y', 'message': 'm'},
        {'row_index': 3, 'column': 'b', 'error_type': 'y', 'message': 'm'},
    ]
    groups = _group_insert_errors(row_errors)
    assert groups[0]['column'] == 'b'
    assert groups[0]['count'] == 3


def test_group_insert_errors_empty_list():
    from flowforge.steps.bulk_load import _group_insert_errors
    assert _group_insert_errors([]) == []


# ─── _insert_error_summary ───────────────────────────────────────────────────

def test_insert_error_summary_empty():
    from flowforge.steps.bulk_load import _insert_error_summary
    assert _insert_error_summary([], 20) == ''


def test_insert_error_summary_counts_types_and_rows():
    from flowforge.steps.bulk_load import _insert_error_summary
    row_errors = [
        {'row_index': 0, 'column': 'email', 'error_type': 'not_null_violation', 'message': 'm'},
        {'row_index': 1, 'column': 'email', 'error_type': 'not_null_violation', 'message': 'm'},
        {'row_index': 2, 'column': 'id',    'error_type': 'unique_violation',   'message': 'm'},
    ]
    summary = _insert_error_summary(row_errors, 20)
    assert summary == '2 error types across 3 of 20 sampled rows'


def test_insert_error_summary_singular_error_type():
    from flowforge.steps.bulk_load import _insert_error_summary
    row_errors = [{'row_index': 0, 'column': 'email', 'error_type': 'not_null_violation', 'message': 'm'}]
    summary = _insert_error_summary(row_errors, 20)
    assert summary == '1 error type across 1 of 20 sampled rows'


# ─── _dry_run_insert_rows ─────────────────────────────────────────────────────

def _mock_db_conn():
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    return conn, cur


def test_dry_run_insert_rows_all_succeed_returns_no_errors():
    from flowforge.steps.bulk_load import _dry_run_insert_rows
    conn, cur = _mock_db_conn()
    with patch('flowforge.steps.bulk_load._open_raw_connection', return_value=conn):
        errors = _dry_run_insert_rows({'_db_type': 'postgresql'}, 'public.t', ['id', 'name'], [['1', 'a'], ['2', 'b']])
    assert errors == []


def test_dry_run_insert_rows_never_commits_always_rolls_back():
    from flowforge.steps.bulk_load import _dry_run_insert_rows
    conn, cur = _mock_db_conn()
    with patch('flowforge.steps.bulk_load._open_raw_connection', return_value=conn):
        _dry_run_insert_rows({'_db_type': 'postgresql'}, 'public.t', ['id'], [['1']])
    conn.commit.assert_not_called()
    conn.rollback.assert_called_once()
    conn.close.assert_called_once()


def test_dry_run_insert_rows_isolates_failure_via_savepoint_and_continues():
    from flowforge.steps.bulk_load import _dry_run_insert_rows
    conn, cur = _mock_db_conn()

    def execute_side_effect(sql, params=None):
        if sql.startswith('INSERT') and params == ['bad']:
            raise Exception('null value in column "name" violates not-null constraint')

    cur.execute.side_effect = execute_side_effect

    with patch('flowforge.steps.bulk_load._open_raw_connection', return_value=conn):
        errors = _dry_run_insert_rows(
            {'_db_type': 'postgresql'}, 'public.t', ['name'], [['ok1'], ['bad'], ['ok2']],
        )

    assert len(errors) == 1
    assert errors[0]['row_index'] == 1
    assert errors[0]['error_type'] == 'not_null_violation'

    executed_sql = [c.args[0] for c in cur.execute.call_args_list]
    assert 'ROLLBACK TO SAVEPOINT ff_dry_run_row' in executed_sql
    # the row after the failure must still have been attempted
    assert executed_sql.count('SAVEPOINT ff_dry_run_row') == 3


def test_dry_run_insert_rows_no_columns_or_rows_short_circuits():
    from flowforge.steps.bulk_load import _dry_run_insert_rows
    assert _dry_run_insert_rows({'_db_type': 'postgresql'}, 't', [], [['1']]) == []
    assert _dry_run_insert_rows({'_db_type': 'postgresql'}, 't', ['id'], []) == []


# ─── preview_bulk_load(dry_run=True) end-to-end ──────────────────────────────

def _base_cfg(src_dir: str, target: str = 'public.test_tbl') -> dict:
    return {
        'connection_id':       'conn-1',
        'source_directory':    src_dir,
        'target_table':        target,
        'file_type':           'csv',
        'delimiter':           ',',
        'header_rows':         1,
        'footer_rows':         0,
        'column_mapping':      [],
        'use_sqlloader':       False,
    }


def test_preview_dry_run_false_never_touches_db(tmp_path):
    """dry_run defaults to False — must not call _dry_run_insert_rows at all."""
    from flowforge.steps.bulk_load import preview_bulk_load
    _write_csv(tmp_path / 'a.csv', [['1', 'alice']], header=['id', 'name'])
    cfg = _base_cfg(str(tmp_path))
    with patch('flowforge.steps.bulk_load._fetch_table_columns', return_value={'id', 'name'}), \
         patch('flowforge.steps.bulk_load._dry_run_insert_rows') as mock_dry_run:
        result = preview_bulk_load(cfg)
    mock_dry_run.assert_not_called()
    assert result['error_groups'] == []
    assert result['insert_error_summary'] == ''


def test_preview_dry_run_true_reports_grouped_errors(tmp_path):
    from flowforge.steps.bulk_load import preview_bulk_load
    _write_csv(tmp_path / 'a.csv', [['1', ''], ['2', 'bob']], header=['id', 'name'])
    cfg = _base_cfg(str(tmp_path))
    fake_errors = [{'row_index': 0, 'column': 'name', 'error_type': 'not_null_violation', 'message': 'null value'}]
    with patch('flowforge.steps.bulk_load._fetch_table_columns', return_value={'id', 'name'}), \
         patch('flowforge.steps.bulk_load._resolve_connection', return_value={'_db_type': 'postgresql'}), \
         patch('flowforge.steps.bulk_load._dry_run_insert_rows', return_value=fake_errors) as mock_dry_run:
        result = preview_bulk_load(cfg, dry_run=True)
    mock_dry_run.assert_called_once()
    assert result['error_groups'] == [{
        'column': 'name', 'error_type': 'not_null_violation', 'message': 'null value',
        'row_indices': [0], 'count': 1,
    }]
    assert result['insert_error_summary'] == '1 error type across 1 of 2 sampled rows'


def test_preview_dry_run_skipped_when_columns_missing(tmp_path):
    """If the CSV has columns not in the target table, the insert test is
    skipped — that mismatch is already reported by the existing warning."""
    from flowforge.steps.bulk_load import preview_bulk_load
    _write_csv(tmp_path / 'a.csv', [['1', 'alice']], header=['id', 'email'])
    cfg = _base_cfg(str(tmp_path))
    with patch('flowforge.steps.bulk_load._fetch_table_columns', return_value={'id', 'name'}), \
         patch('flowforge.steps.bulk_load._dry_run_insert_rows') as mock_dry_run:
        result = preview_bulk_load(cfg, dry_run=True)
    mock_dry_run.assert_not_called()
    assert any('email' in w and 'not found' in w for w in result['warnings'])


def test_preview_dry_run_skipped_for_sqlloader_path_with_warning(tmp_path):
    from flowforge.steps.bulk_load import preview_bulk_load
    _write_csv(tmp_path / 'a.csv', [['1', 'alice']], header=['id', 'name'])
    cfg = _base_cfg(str(tmp_path))
    cfg['use_sqlloader'] = True
    with patch('flowforge.steps.bulk_load._fetch_table_columns', return_value={'id', 'name'}), \
         patch('flowforge.steps.bulk_load._resolve_connection', return_value={'_db_type': 'oracle'}), \
         patch('flowforge.steps.bulk_load._dry_run_insert_rows') as mock_dry_run:
        result = preview_bulk_load(cfg, dry_run=True)
    mock_dry_run.assert_not_called()
    assert any('SQL*Loader' in w for w in result['warnings'])


def test_preview_dry_run_connection_open_failure_warns(tmp_path):
    from flowforge.steps.bulk_load import preview_bulk_load
    _write_csv(tmp_path / 'a.csv', [['1', 'alice']], header=['id', 'name'])
    cfg = _base_cfg(str(tmp_path))
    with patch('flowforge.steps.bulk_load._fetch_table_columns', return_value={'id', 'name'}), \
         patch('flowforge.steps.bulk_load._resolve_connection', side_effect=RuntimeError('conn refused')):
        result = preview_bulk_load(cfg, dry_run=True)
    assert any('conn refused' in w for w in result['warnings'])


def test_preview_dry_run_no_errors_yields_empty_groups(tmp_path):
    from flowforge.steps.bulk_load import preview_bulk_load
    _write_csv(tmp_path / 'a.csv', [['1', 'alice']], header=['id', 'name'])
    cfg = _base_cfg(str(tmp_path))
    with patch('flowforge.steps.bulk_load._fetch_table_columns', return_value={'id', 'name'}), \
         patch('flowforge.steps.bulk_load._resolve_connection', return_value={'_db_type': 'postgresql'}), \
         patch('flowforge.steps.bulk_load._dry_run_insert_rows', return_value=[]):
        result = preview_bulk_load(cfg, dry_run=True)
    assert result['error_groups'] == []
    assert result['insert_error_summary'] == ''
