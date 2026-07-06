"""Unit tests for preview_bulk_load() and _fetch_table_columns() — the
dry-run "Test File" path that checks file discovery, header parsing, and
target-column existence without loading any data."""
import csv
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _write_csv(path: Path, rows: list[list[str]], header: list[str] | None = None, delimiter: str = ','):
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.writer(fh, delimiter=delimiter)
        if header:
            writer.writerow(header)
        writer.writerows(rows)


def _base_cfg(src_dir: str, target: str = 'public.test_tbl') -> dict:
    return {
        'connection_id':       '',
        'source_directory':    src_dir,
        'target_table':        target,
        'file_type':           'csv',
        'delimiter':           ',',
        'header_rows':         1,
        'footer_rows':         0,
        'column_mapping':      [],
    }


def _fake_conn(columns: list[str] | None):
    """Context-manager mock standing in for get_connection()'s return value."""
    conn = MagicMock()
    conn.db_type = 'postgresql'
    conn.execute_query.return_value = [(c,) for c in columns] if columns is not None else []
    conn.__enter__.return_value = conn
    conn.__exit__.return_value = False
    return conn


# ─── Hard-stop validation errors ────────────────────────────────────────────

def test_missing_source_directory():
    from flowforge.steps.bulk_load import preview_bulk_load
    with pytest.raises(ValueError, match='source_directory is required'):
        preview_bulk_load(_base_cfg(''))


def test_nonexistent_source_directory(tmp_path):
    from flowforge.steps.bulk_load import preview_bulk_load
    cfg = _base_cfg(str(tmp_path / 'does-not-exist'))
    with pytest.raises(ValueError, match='source_directory not found'):
        preview_bulk_load(cfg)


def test_invalid_delimiter(tmp_path):
    from flowforge.steps.bulk_load import preview_bulk_load
    cfg = _base_cfg(str(tmp_path))
    cfg['delimiter'] = '||'
    with pytest.raises(ValueError, match='invalid delimiter'):
        preview_bulk_load(cfg)


def test_no_matching_files(tmp_path):
    from flowforge.steps.bulk_load import preview_bulk_load
    cfg = _base_cfg(str(tmp_path))
    with pytest.raises(ValueError, match='no files found'):
        preview_bulk_load(cfg)


def test_file_type_and_prefix_filtering(tmp_path):
    from flowforge.steps.bulk_load import preview_bulk_load
    _write_csv(tmp_path / 'OTHER_1.csv', [['1', 'a']], header=['id', 'name'])
    _write_csv(tmp_path / 'data.txt', [['1', 'a']], header=['id', 'name'])
    cfg = _base_cfg(str(tmp_path))
    cfg['file_prefix'] = 'SUBS_'
    with pytest.raises(ValueError, match='no files found'):
        preview_bulk_load(cfg)


def test_file_prefix_exclude_filtering(tmp_path):
    from flowforge.steps.bulk_load import preview_bulk_load
    _write_csv(tmp_path / 'SUBS_SKIP_1.csv', [['1', 'a']], header=['id', 'name'])
    cfg = _base_cfg(str(tmp_path))
    cfg['file_prefix'] = 'SUBS_'
    cfg['file_prefix_exclude'] = 'SUBS_SKIP_'
    with pytest.raises(ValueError, match='no files found'):
        preview_bulk_load(cfg)


def test_no_data_rows_after_stripping_header_footer(tmp_path):
    from flowforge.steps.bulk_load import preview_bulk_load
    _write_csv(tmp_path / 'a.csv', [], header=['id', 'name'])
    cfg = _base_cfg(str(tmp_path))
    with pytest.raises(ValueError, match='no data rows'):
        preview_bulk_load(cfg)


def test_invalid_column_name_in_header_raises(tmp_path):
    from flowforge.steps.bulk_load import preview_bulk_load
    _write_csv(tmp_path / 'a.csv', [['1', 'x']], header=['id', 'bad col!'])
    cfg = _base_cfg(str(tmp_path))
    with pytest.raises(ValueError, match='a.csv'):
        preview_bulk_load(cfg)


# ─── Successful preview + warnings ──────────────────────────────────────────

def test_single_file_no_warnings_without_target_table(tmp_path):
    from flowforge.steps.bulk_load import preview_bulk_load
    _write_csv(tmp_path / 'a.csv', [['1', 'alice'], ['2', 'bob']], header=['id', 'name'])
    cfg = _base_cfg(str(tmp_path), target='')
    result = preview_bulk_load(cfg)
    assert result['file_name'] == 'a.csv'
    assert result['files_matched'] == 1
    assert result['columns'] == ['id', 'name']
    assert result['row_count_sampled'] == 2
    assert result['sample_rows'] == [['1', 'alice'], ['2', 'bob']]
    assert any('target_table not set' in w for w in result['warnings'])


def test_multiple_files_warns_and_picks_first_alphabetically(tmp_path):
    from flowforge.steps.bulk_load import preview_bulk_load
    _write_csv(tmp_path / 'b.csv', [['2', 'b']], header=['id', 'name'])
    _write_csv(tmp_path / 'a.csv', [['1', 'a']], header=['id', 'name'])
    cfg = _base_cfg(str(tmp_path), target='')
    result = preview_bulk_load(cfg)
    assert result['file_name'] == 'a.csv'
    assert result['files_matched'] == 2
    assert any('2 files match' in w for w in result['warnings'])


def test_no_connection_selected_warns(tmp_path):
    from flowforge.steps.bulk_load import preview_bulk_load
    _write_csv(tmp_path / 'a.csv', [['1', 'alice']], header=['id', 'name'])
    cfg = _base_cfg(str(tmp_path))
    cfg['connection_id'] = ''
    result = preview_bulk_load(cfg)
    assert any('No connection selected' in w for w in result['warnings'])


def test_ragged_row_length_warns(tmp_path):
    from flowforge.steps.bulk_load import preview_bulk_load
    with open(tmp_path / 'a.csv', 'w', newline='', encoding='utf-8') as fh:
        fh.write('id,name\n1,alice\n2,bob,extra\n')
    cfg = _base_cfg(str(tmp_path), target='')
    result = preview_bulk_load(cfg)
    assert any('different' in w and 'delimiter' in w for w in result['warnings'])


def test_header_rows_zero_generates_positional_columns(tmp_path):
    from flowforge.steps.bulk_load import preview_bulk_load
    _write_csv(tmp_path / 'a.csv', [['1', 'alice'], ['2', 'bob']])
    cfg = _base_cfg(str(tmp_path), target='')
    cfg['header_rows'] = 0
    result = preview_bulk_load(cfg)
    assert result['columns'] == ['col0', 'col1']


def test_column_mapping_applied_to_header(tmp_path):
    from flowforge.steps.bulk_load import preview_bulk_load
    _write_csv(tmp_path / 'a.csv', [['1', 'alice']], header=['FIRST_NAME', 'id'])
    cfg = _base_cfg(str(tmp_path), target='')
    cfg['column_mapping'] = [{'source': 'FIRST_NAME', 'target': 'first_name'}]
    result = preview_bulk_load(cfg)
    assert result['columns'] == ['first_name', 'id']


def test_sample_rows_capped_at_20(tmp_path):
    from flowforge.steps.bulk_load import preview_bulk_load
    rows = [[str(i), f'name{i}'] for i in range(30)]
    _write_csv(tmp_path / 'a.csv', rows, header=['id', 'name'])
    cfg = _base_cfg(str(tmp_path), target='')
    result = preview_bulk_load(cfg)
    assert result['row_count_sampled'] == 20
    assert len(result['sample_rows']) == 20


def test_non_utf8_file_raises_value_error(tmp_path):
    from flowforge.steps.bulk_load import preview_bulk_load
    p = tmp_path / 'a.csv'
    p.write_bytes(b'id,name\n1,\xff\xfe invalid utf8\n')
    cfg = _base_cfg(str(tmp_path), target='')
    with pytest.raises(ValueError, match='could not read'):
        preview_bulk_load(cfg)


# ─── Target-table column checks (mocked connection) ─────────────────────────

def test_target_table_columns_match_no_warning(tmp_path):
    from flowforge.steps.bulk_load import preview_bulk_load
    _write_csv(tmp_path / 'a.csv', [['1', 'alice']], header=['id', 'name'])
    cfg = _base_cfg(str(tmp_path))
    cfg['connection_id'] = 'conn-1'
    with patch('flowforge.steps.bulk_load._fetch_table_columns', return_value={'id', 'name', 'extra'}):
        result = preview_bulk_load(cfg)
    assert not any('not found in' in w for w in result['warnings'])
    assert not any('does not exist' in w for w in result['warnings'])


def test_target_table_missing_columns_warns(tmp_path):
    from flowforge.steps.bulk_load import preview_bulk_load
    _write_csv(tmp_path / 'a.csv', [['1', 'alice']], header=['id', 'email'])
    cfg = _base_cfg(str(tmp_path))
    cfg['connection_id'] = 'conn-1'
    with patch('flowforge.steps.bulk_load._fetch_table_columns', return_value={'id', 'name'}):
        result = preview_bulk_load(cfg)
    assert any('email' in w and 'not found' in w for w in result['warnings'])


def test_target_table_does_not_exist_warns(tmp_path):
    from flowforge.steps.bulk_load import preview_bulk_load
    _write_csv(tmp_path / 'a.csv', [['1', 'alice']], header=['id', 'name'])
    cfg = _base_cfg(str(tmp_path))
    cfg['connection_id'] = 'conn-1'
    with patch('flowforge.steps.bulk_load._fetch_table_columns', return_value=None):
        result = preview_bulk_load(cfg)
    assert any('does not exist' in w for w in result['warnings'])


def test_invalid_target_table_identifier_warns(tmp_path):
    from flowforge.steps.bulk_load import preview_bulk_load
    _write_csv(tmp_path / 'a.csv', [['1', 'alice']], header=['id', 'name'])
    cfg = _base_cfg(str(tmp_path), target='bad table; drop')
    cfg['connection_id'] = 'conn-1'
    result = preview_bulk_load(cfg)
    assert any('Invalid target_table' in w for w in result['warnings'])


def test_unexpected_connection_error_warns_generically(tmp_path):
    from flowforge.steps.bulk_load import preview_bulk_load
    _write_csv(tmp_path / 'a.csv', [['1', 'alice']], header=['id', 'name'])
    cfg = _base_cfg(str(tmp_path))
    cfg['connection_id'] = 'conn-1'
    with patch('flowforge.steps.bulk_load._fetch_table_columns', side_effect=RuntimeError('boom')):
        result = preview_bulk_load(cfg)
    assert any('Could not verify target table columns' in w and 'boom' in w for w in result['warnings'])


# ─── _fetch_table_columns ────────────────────────────────────────────────────

def test_fetch_table_columns_postgres_no_schema():
    from flowforge.steps.bulk_load import _fetch_table_columns
    fake_conn = _fake_conn(['id', 'name'])
    with patch('flowforge.connections.factory.get_connection', return_value=fake_conn):
        cols = _fetch_table_columns('conn-1', 'my_table')
    assert cols == {'id', 'name'}
    args, _ = fake_conn.execute_query.call_args
    assert args[1] == ('my_table', 'public')


def test_fetch_table_columns_postgres_with_schema():
    from flowforge.steps.bulk_load import _fetch_table_columns
    fake_conn = _fake_conn(['id'])
    with patch('flowforge.connections.factory.get_connection', return_value=fake_conn):
        cols = _fetch_table_columns('conn-1', 'staging.my_table')
    assert cols == {'id'}
    args, _ = fake_conn.execute_query.call_args
    assert args[1] == ('my_table', 'staging')


def test_fetch_table_columns_oracle_no_schema():
    from flowforge.steps.bulk_load import _fetch_table_columns
    fake_conn = _fake_conn(['ID', 'NAME'])
    fake_conn.db_type = 'oracle'
    with patch('flowforge.connections.factory.get_connection', return_value=fake_conn):
        cols = _fetch_table_columns('conn-1', 'MY_TABLE')
    assert cols == {'id', 'name'}
    query, params = fake_conn.execute_query.call_args[0]
    assert 'user_tab_columns' in query
    assert params == ('MY_TABLE',)


def test_fetch_table_columns_oracle_with_schema():
    from flowforge.steps.bulk_load import _fetch_table_columns
    fake_conn = _fake_conn(['ID'])
    fake_conn.db_type = 'oracle'
    with patch('flowforge.connections.factory.get_connection', return_value=fake_conn):
        cols = _fetch_table_columns('conn-1', 'SCHEMA1.MY_TABLE')
    assert cols == {'id'}
    query, params = fake_conn.execute_query.call_args[0]
    assert 'all_tab_columns' in query
    assert params == ('MY_TABLE', 'SCHEMA1')


def test_fetch_table_columns_returns_none_when_table_missing():
    from flowforge.steps.bulk_load import _fetch_table_columns
    fake_conn = _fake_conn(None)
    with patch('flowforge.connections.factory.get_connection', return_value=fake_conn):
        cols = _fetch_table_columns('conn-1', 'ghost_table')
    assert cols is None


def test_fetch_table_columns_strips_quoted_identifier():
    from flowforge.steps.bulk_load import _fetch_table_columns
    fake_conn = _fake_conn(['id'])
    with patch('flowforge.connections.factory.get_connection', return_value=fake_conn):
        cols = _fetch_table_columns('conn-1', '"public"."my_table"')
    assert cols == {'id'}
    args, _ = fake_conn.execute_query.call_args
    assert args[1] == ('my_table', 'public')
