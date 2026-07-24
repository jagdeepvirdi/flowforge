"""Unit tests for BulkLoadStep and its supporting helpers.

These tests mock _resolve_connection and _open_raw_connection so no live
database is needed.  Only the Python-fallback execution path is exercised
here; the PostgreSQL COPY path is covered separately via live-DB tests in
test_bulk_load_postgres.py (optional, requires DB).
"""
import csv
from pathlib import Path
from unittest.mock import MagicMock, patch

from flowforge.steps.base import BaseStep, StepResult

# ─── Shared helpers ───────────────────────────────────────────────────────────

def _write_csv(path: Path, rows: list[list[str]], header: list[str] | None = None):
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.writer(fh)
        if header:
            writer.writerow(header)
        writer.writerows(rows)


def _base_cfg(src_dir: str, target: str = 'public.test_tbl') -> dict:
    """Minimal valid inline config for BulkLoadStep."""
    return {
        'connection_id':       'conn-test-uuid',
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


def _pg_conn_cfg() -> dict:
    """Fake resolved connection config that triggers the Python fallback path.

    'mysql' (not 'postgresql'/'oracle') routes to the fallback per
    _dispatch_single_file, and is a real registered db_type — needed since
    _make_placeholders() (MAINT-01) resolves it via the connections registry,
    unlike the arbitrary 'other' sentinel this used to be.
    """
    return {'_db_type': 'mysql'}


def _mock_db_conn():
    """Return (conn, cursor) mocks that behave like a psycopg2 connection."""
    conn = MagicMock()
    cur  = MagicMock()
    cur.rowcount = -1
    conn.cursor.return_value = cur
    return conn, cur


def run_step(cfg: dict, conn_cfg=None, raw_conn=None) -> StepResult:
    from flowforge.steps.bulk_load import BulkLoadStep
    step = BulkLoadStep('bulk', cfg)

    patches: list = []
    if conn_cfg is not None:
        patches.append(patch('flowforge.steps.bulk_load._resolve_connection',
                             return_value=conn_cfg))
    if raw_conn is not None:
        patches.append(patch('flowforge.steps.bulk_load._open_raw_connection',
                             return_value=raw_conn))

    # Apply patches one by one using ExitStack-style nesting
    result = None  # noqa: F841

    def _run_with_patches(remaining, step, cfg):
        if not remaining:
            return step.run({})
        p, *rest = remaining
        with p:
            return _run_with_patches(rest, step, cfg)

    return _run_with_patches(patches, step, cfg)


# ─── Validation failures ──────────────────────────────────────────────────────

def test_missing_connection_id(tmp_path):
    from flowforge.steps.bulk_load import BulkLoadStep
    cfg = _base_cfg(str(tmp_path))
    cfg['connection_id'] = ''
    result = BulkLoadStep('bulk', cfg).run({})
    assert result.success is False
    assert 'connection_id' in result.error


def test_missing_source_directory():
    from flowforge.steps.bulk_load import BulkLoadStep
    cfg = _base_cfg('')
    result = BulkLoadStep('bulk', cfg).run({})
    assert result.success is False
    assert 'source_directory' in result.error


def test_missing_target_table(tmp_path):
    from flowforge.steps.bulk_load import BulkLoadStep
    cfg = _base_cfg(str(tmp_path))
    cfg['target_table'] = ''
    result = BulkLoadStep('bulk', cfg).run({})
    assert result.success is False
    assert 'target_table' in result.error


def test_nonexistent_source_directory():
    from flowforge.steps.bulk_load import BulkLoadStep
    cfg = _base_cfg('/does/not/exist/anywhere/at/all')
    with patch('flowforge.steps.bulk_load._resolve_connection',
               return_value=_pg_conn_cfg()):
        result = BulkLoadStep('bulk', cfg).run({})
    assert result.success is False
    assert 'not found' in result.error


# ─── File scanning / on_no_files ─────────────────────────────────────────────

def test_on_no_files_skip_returns_success(tmp_path):
    from flowforge.steps.bulk_load import BulkLoadStep
    cfg = _base_cfg(str(tmp_path))
    cfg['on_no_files'] = 'skip'
    with patch('flowforge.steps.bulk_load._resolve_connection',
               return_value=_pg_conn_cfg()):
        result = BulkLoadStep('bulk', cfg).run({})
    assert result.success is True
    assert result.files_found == 0
    assert result.files_loaded == 0
    assert result.records_loaded == 0


def test_on_no_files_fail_returns_failure(tmp_path):
    from flowforge.steps.bulk_load import BulkLoadStep
    cfg = _base_cfg(str(tmp_path))
    cfg['on_no_files'] = 'fail'
    with patch('flowforge.steps.bulk_load._resolve_connection',
               return_value=_pg_conn_cfg()):
        result = BulkLoadStep('bulk', cfg).run({})
    assert result.success is False


def test_file_prefix_filtering(tmp_path):
    """Only files matching file_prefix are picked up; others ignored."""
    _write_csv(tmp_path / 'SUBS_001.csv', [['Alice', '30']], header=['name', 'age'])
    _write_csv(tmp_path / 'ORDERS_001.csv', [['ORD-1', '99']], header=['id', 'amt'])

    from flowforge.steps.bulk_load import BulkLoadStep
    cfg = _base_cfg(str(tmp_path))
    cfg['file_prefix'] = 'SUBS_'

    conn, _ = _mock_db_conn()
    with patch('flowforge.steps.bulk_load._resolve_connection', return_value=_pg_conn_cfg()), \
         patch('flowforge.steps.bulk_load._open_raw_connection', return_value=conn):
        result = BulkLoadStep('bulk', cfg).run({})

    assert result.files_found == 1
    assert result.files_loaded == 1


def test_file_prefix_exclude_filtering(tmp_path):
    """Files matching file_prefix_exclude are skipped even if the main prefix matches."""
    _write_csv(tmp_path / 'SUBS_001.csv',      [['Alice', '30']], header=['name', 'age'])
    _write_csv(tmp_path / 'SUBS_SKIP_001.csv', [['Bob',   '25']], header=['name', 'age'])

    from flowforge.steps.bulk_load import BulkLoadStep
    cfg = _base_cfg(str(tmp_path))
    cfg['file_prefix']         = 'SUBS_'
    cfg['file_prefix_exclude'] = 'SUBS_SKIP_'

    conn, _ = _mock_db_conn()
    with patch('flowforge.steps.bulk_load._resolve_connection', return_value=_pg_conn_cfg()), \
         patch('flowforge.steps.bulk_load._open_raw_connection', return_value=conn):
        result = BulkLoadStep('bulk', cfg).run({})

    assert result.files_found == 1   # ORDERS excluded by prefix
    assert result.files_loaded == 1


def test_multiple_files_all_loaded(tmp_path):
    _write_csv(tmp_path / 'a.csv', [['Alice', '30']], header=['name', 'age'])
    _write_csv(tmp_path / 'b.csv', [['Bob',   '25']], header=['name', 'age'])

    from flowforge.steps.bulk_load import BulkLoadStep
    conn, _ = _mock_db_conn()
    with patch('flowforge.steps.bulk_load._resolve_connection', return_value=_pg_conn_cfg()), \
         patch('flowforge.steps.bulk_load._open_raw_connection', return_value=conn):
        result = BulkLoadStep('bulk', _base_cfg(str(tmp_path))).run({})

    assert result.files_found == 2
    assert result.files_loaded == 2


# ─── Python-fallback execution ────────────────────────────────────────────────

def test_python_fallback_strips_header(tmp_path):
    """executemany must not receive the header row as data."""
    _write_csv(tmp_path / 'data.csv', [['Alice', '30'], ['Bob', '25']],
               header=['name', 'age'])

    from flowforge.steps.bulk_load import BulkLoadStep
    conn, cur = _mock_db_conn()
    with patch('flowforge.steps.bulk_load._resolve_connection', return_value=_pg_conn_cfg()), \
         patch('flowforge.steps.bulk_load._open_raw_connection', return_value=conn):
        result = BulkLoadStep('bulk', _base_cfg(str(tmp_path))).run({})

    assert result.success is True
    assert result.records_loaded == 2
    called_rows = cur.executemany.call_args[0][1]
    # header must not be one of the data rows
    assert ['name', 'age'] not in called_rows


def test_python_fallback_strips_footer(tmp_path):
    """Footer rows are excluded from the INSERT."""
    _write_csv(tmp_path / 'data.csv',
               [['Alice', '30'], ['Bob', '25'], ['TOTAL', '55']],
               header=['name', 'age'])

    from flowforge.steps.bulk_load import BulkLoadStep
    cfg = _base_cfg(str(tmp_path))
    cfg['footer_rows'] = 1

    conn, cur = _mock_db_conn()
    with patch('flowforge.steps.bulk_load._resolve_connection', return_value=_pg_conn_cfg()), \
         patch('flowforge.steps.bulk_load._open_raw_connection', return_value=conn):
        result = BulkLoadStep('bulk', cfg).run({})

    assert result.records_loaded == 2
    called_rows = cur.executemany.call_args[0][1]
    first_col_values = [r[0] for r in called_rows]
    assert 'TOTAL' not in first_col_values


def test_python_fallback_replace_mode_truncates(tmp_path):
    """Replace mode must TRUNCATE before inserting."""
    _write_csv(tmp_path / 'data.csv', [['Alice', '30']], header=['name', 'age'])

    from flowforge.steps.bulk_load import BulkLoadStep
    cfg = _base_cfg(str(tmp_path))
    cfg['load_mode'] = 'replace'

    conn, cur = _mock_db_conn()
    with patch('flowforge.steps.bulk_load._resolve_connection', return_value=_pg_conn_cfg()), \
         patch('flowforge.steps.bulk_load._open_raw_connection', return_value=conn):
        BulkLoadStep('bulk', cfg).run({})

    execute_sqls = [c[0][0] for c in cur.execute.call_args_list]
    assert any('TRUNCATE' in sql for sql in execute_sqls)


def test_python_fallback_append_mode_no_truncate(tmp_path):
    """Append mode must NOT emit a TRUNCATE."""
    _write_csv(tmp_path / 'data.csv', [['Alice', '30']], header=['name', 'age'])

    from flowforge.steps.bulk_load import BulkLoadStep
    cfg = _base_cfg(str(tmp_path))
    cfg['load_mode'] = 'append'

    conn, cur = _mock_db_conn()
    with patch('flowforge.steps.bulk_load._resolve_connection', return_value=_pg_conn_cfg()), \
         patch('flowforge.steps.bulk_load._open_raw_connection', return_value=conn):
        BulkLoadStep('bulk', cfg).run({})

    execute_sqls = [c[0][0] for c in cur.execute.call_args_list]
    assert not any('TRUNCATE' in sql for sql in execute_sqls)


# ─── Multi-file replace mode (regression: truncate must only fire once) ──────

def test_replace_mode_truncates_once_across_multiple_files(tmp_path):
    """Each file's own 'replace' truncate must not wipe out rows the previous
    file in the *same run* just inserted — only the first file should trigger
    a TRUNCATE; every later file in that run must append instead."""
    _write_csv(tmp_path / 'a.csv', [['Alice', '30']], header=['name', 'age'])
    _write_csv(tmp_path / 'b.csv', [['Bob', '25']], header=['name', 'age'])

    from flowforge.steps.bulk_load import BulkLoadStep
    cfg = _base_cfg(str(tmp_path))
    cfg['load_mode'] = 'replace'

    conn, cur = _mock_db_conn()
    with patch('flowforge.steps.bulk_load._resolve_connection', return_value=_pg_conn_cfg()), \
         patch('flowforge.steps.bulk_load._open_raw_connection', return_value=conn):
        result = BulkLoadStep('bulk', cfg).run({})

    execute_sqls = [c[0][0] for c in cur.execute.call_args_list]
    truncate_calls = [sql for sql in execute_sqls if 'TRUNCATE' in sql]
    assert len(truncate_calls) == 1, f'expected exactly one TRUNCATE across the run, got {len(truncate_calls)}'
    assert cur.executemany.call_count == 2, 'both files should have attempted an insert'
    assert result.success is True
    assert result.records_loaded == 2


def test_effective_load_mode_only_replace_on_first_file(tmp_path):
    """run() must pass the configured load_mode to only the first file and
    force 'append' for every file after it in the same batch, regardless of
    the configured mode — this is what stops file N's truncate from wiping
    out file 1..N-1's inserts within the same run."""
    _write_csv(tmp_path / 'a.csv', [['Alice']], header=['name'])
    _write_csv(tmp_path / 'b.csv', [['Bob']], header=['name'])
    _write_csv(tmp_path / 'c.csv', [['Carol']], header=['name'])

    from flowforge.steps.bulk_load import BulkLoadStep
    cfg = _base_cfg(str(tmp_path))
    cfg['load_mode'] = 'replace'

    seen_modes: list[str] = []

    def _dispatch_side_effect(db_type, use_sqlloader, conn_cfg, file_path,
                               delimiter, header_rows, footer_rows,
                               target_table, load_mode, column_mapping):
        seen_modes.append(load_mode)
        return 1, 0, 'ok'

    with patch('flowforge.steps.bulk_load._resolve_connection', return_value=_pg_conn_cfg()), \
         patch('flowforge.steps.bulk_load._dispatch_single_file', side_effect=_dispatch_side_effect):
        result = BulkLoadStep('bulk', cfg).run({})

    assert seen_modes == ['replace', 'append', 'append']
    assert result.success is True


def test_effective_load_mode_unaffected_when_configured_append(tmp_path):
    """Sanity check: when the configured mode is already 'append', every file
    keeps seeing 'append' — the first-file special-case only matters for 'replace'."""
    _write_csv(tmp_path / 'a.csv', [['Alice']], header=['name'])
    _write_csv(tmp_path / 'b.csv', [['Bob']], header=['name'])

    from flowforge.steps.bulk_load import BulkLoadStep
    cfg = _base_cfg(str(tmp_path))
    cfg['load_mode'] = 'append'

    seen_modes: list[str] = []

    def _dispatch_side_effect(db_type, use_sqlloader, conn_cfg, file_path,
                               delimiter, header_rows, footer_rows,
                               target_table, load_mode, column_mapping):
        seen_modes.append(load_mode)
        return 1, 0, 'ok'

    with patch('flowforge.steps.bulk_load._resolve_connection', return_value=_pg_conn_cfg()), \
         patch('flowforge.steps.bulk_load._dispatch_single_file', side_effect=_dispatch_side_effect):
        BulkLoadStep('bulk', cfg).run({})

    assert seen_modes == ['append', 'append']


def test_python_fallback_uses_column_mapping(tmp_path):
    """Column mapping renames source header columns in the INSERT SQL."""
    _write_csv(tmp_path / 'data.csv', [['Alice', '30']], header=['FIRST_NAME', 'AGE'])

    from flowforge.steps.bulk_load import BulkLoadStep
    cfg = _base_cfg(str(tmp_path))
    cfg['column_mapping'] = [
        {'source': 'FIRST_NAME', 'target': 'first_name'},
        {'source': 'AGE',        'target': 'age'},
    ]

    conn, cur = _mock_db_conn()
    with patch('flowforge.steps.bulk_load._resolve_connection', return_value=_pg_conn_cfg()), \
         patch('flowforge.steps.bulk_load._open_raw_connection', return_value=conn):
        BulkLoadStep('bulk', cfg).run({})

    insert_sql = cur.executemany.call_args[0][0]
    assert 'first_name' in insert_sql
    assert 'age' in insert_sql
    assert 'FIRST_NAME' not in insert_sql


# ─── StepResult output variable fields ───────────────────────────────────────

def test_step_result_fields_populated(tmp_path):
    """files_found, files_loaded, records_loaded must be correctly set."""
    _write_csv(tmp_path / 'a.csv', [['Alice', '30'], ['Bob', '25']], header=['name', 'age'])
    _write_csv(tmp_path / 'b.csv', [['Carol', '40']], header=['name', 'age'])

    from flowforge.steps.bulk_load import BulkLoadStep
    conn, _ = _mock_db_conn()
    with patch('flowforge.steps.bulk_load._resolve_connection', return_value=_pg_conn_cfg()), \
         patch('flowforge.steps.bulk_load._open_raw_connection', return_value=conn):
        result = BulkLoadStep('bulk', _base_cfg(str(tmp_path))).run({})

    assert result.success is True
    assert result.files_found == 2
    assert result.files_loaded == 2
    assert result.files_failed == 0
    assert result.records_loaded == 3
    assert result.records_failed == 0
    assert result.duration_sec >= 0.0
    assert result.rows_affected == 3  # mirrors records_loaded


def test_skip_result_has_zero_counts(tmp_path):
    """on_no_files=skip should set all counts to zero and succeed."""
    from flowforge.steps.bulk_load import BulkLoadStep
    cfg = _base_cfg(str(tmp_path))
    cfg['on_no_files'] = 'skip'
    with patch('flowforge.steps.bulk_load._resolve_connection', return_value=_pg_conn_cfg()):
        result = BulkLoadStep('bulk', cfg).run({})

    assert result.success is True
    assert result.files_found == 0
    assert result.files_loaded == 0
    assert result.files_failed == 0
    assert result.records_loaded == 0
    assert result.records_failed == 0
    assert result.duration_sec == 0.0


# ─── Archive ──────────────────────────────────────────────────────────────────

def test_archive_moves_file_after_load(tmp_path):
    src_dir     = tmp_path / 'incoming'
    archive_dir = tmp_path / 'archive'
    src_dir.mkdir()
    _write_csv(src_dir / 'data.csv', [['Alice', '30']], header=['name', 'age'])

    from flowforge.steps.bulk_load import BulkLoadStep
    cfg = _base_cfg(str(src_dir))
    cfg['archive_directory'] = str(archive_dir)

    conn, _ = _mock_db_conn()
    with patch('flowforge.steps.bulk_load._resolve_connection', return_value=_pg_conn_cfg()), \
         patch('flowforge.steps.bulk_load._open_raw_connection', return_value=conn):
        result = BulkLoadStep('bulk', cfg).run({})

    assert result.success is True
    assert not (src_dir / 'data.csv').exists(), 'file should have been moved out of incoming'
    assert (archive_dir / 'data.csv').exists(), 'file should be present in archive_dir'


def test_no_archive_when_archive_dir_empty(tmp_path):
    """When archive_directory is empty, files stay in source dir."""
    _write_csv(tmp_path / 'data.csv', [['Alice', '30']], header=['name', 'age'])

    from flowforge.steps.bulk_load import BulkLoadStep
    cfg = _base_cfg(str(tmp_path))
    cfg['archive_directory'] = ''

    conn, _ = _mock_db_conn()
    with patch('flowforge.steps.bulk_load._resolve_connection', return_value=_pg_conn_cfg()), \
         patch('flowforge.steps.bulk_load._open_raw_connection', return_value=conn):
        result = BulkLoadStep('bulk', cfg).run({})

    assert result.success is True
    assert (tmp_path / 'data.csv').exists(), 'file should remain when no archive_dir configured'


# ─── Config resolution (bulk_load_config_id) ─────────────────────────────────

def test_inline_config_used_when_no_config_id(tmp_path):
    """Config without bulk_load_config_id uses inline step config directly."""
    _write_csv(tmp_path / 'data.csv', [['Alice']], header=['name'])

    from flowforge.steps.bulk_load import BulkLoadStep
    cfg = _base_cfg(str(tmp_path))  # no 'bulk_load_config_id' key

    conn, _ = _mock_db_conn()
    with patch('flowforge.steps.bulk_load._resolve_connection', return_value=_pg_conn_cfg()), \
         patch('flowforge.steps.bulk_load._open_raw_connection', return_value=conn):
        result = BulkLoadStep('bulk', cfg).run({})

    assert result.success is True


def test_config_resolved_from_bulk_load_config_id(tmp_path):
    """When bulk_load_config_id is set, _load_bulk_load_config is called once."""
    _write_csv(tmp_path / 'data.csv', [['Alice']], header=['name'])

    from flowforge.steps.bulk_load import BulkLoadStep
    resolved_cfg = _base_cfg(str(tmp_path))

    conn, _ = _mock_db_conn()
    with patch('flowforge.steps.bulk_load._load_bulk_load_config',
               return_value=resolved_cfg) as mock_load, \
         patch('flowforge.steps.bulk_load._resolve_connection', return_value=_pg_conn_cfg()), \
         patch('flowforge.steps.bulk_load._open_raw_connection', return_value=conn):
        result = BulkLoadStep('bulk', {'bulk_load_config_id': 'fake-uuid-123'}).run({})

    mock_load.assert_called_once_with('fake-uuid-123')
    assert result.success is True


def test_unknown_bulk_load_config_id_returns_failure():
    """A bulk_load_config_id that resolves to None produces a clear failure."""
    from flowforge.steps.bulk_load import BulkLoadStep
    with patch('flowforge.steps.bulk_load._load_bulk_load_config', return_value=None):
        result = BulkLoadStep('bulk', {'bulk_load_config_id': 'bad-uuid'}).run({})
    assert result.success is False
    assert 'not found' in result.error


# ─── Runner context propagation ──────────────────────────────────────────────

def test_bulk_load_fields_threaded_to_downstream_step():
    """All six StepResult bulk-load fields must appear in context['steps'] for downstream steps."""

    received: dict = {}

    class FakeBulkStep(BaseStep):
        def run(self, ctx):
            return StepResult(
                success=True,
                files_found=4,
                files_loaded=4,
                files_failed=0,
                records_loaded=80,
                records_failed=2,
                duration_sec=0.55,
            )

    class DownstreamStep(BaseStep):
        def run(self, ctx):
            received.update(ctx)
            return StepResult(success=True)

    with patch('flowforge.engine.runner._create_run_record', return_value=None), \
         patch('flowforge.engine.runner._write_step_run'), \
         patch('flowforge.engine.runner._finish_run_record'):
        from flowforge.engine.runner import run_pipeline
        run_pipeline('Test Bulk Pipeline', [
            FakeBulkStep('loader', {'on_error': 'stop'}),
            DownstreamStep('consumer', {'on_error': 'stop'}),
        ])

    lctx = received['steps']['loader']
    assert lctx['files_found']    == 4
    assert lctx['files_loaded']   == 4
    assert lctx['files_failed']   == 0
    assert lctx['records_loaded'] == 80
    assert lctx['records_failed'] == 2
    assert lctx['duration_sec']   == 0.55


# ─── _col_map_dict helper ─────────────────────────────────────────────────────

def test_col_map_dict_list_form():
    from flowforge.steps.bulk_load import _col_map_dict
    mapping = [
        {'source': 'FIRST_NAME', 'target': 'first_name'},
        {'source': 'LAST_NAME',  'target': 'last_name'},
    ]
    assert _col_map_dict(mapping) == {'FIRST_NAME': 'first_name', 'LAST_NAME': 'last_name'}


def test_col_map_dict_dict_form():
    from flowforge.steps.bulk_load import _col_map_dict
    mapping = {'COL_A': 'col_a', 'COL_B': 'col_b'}
    assert _col_map_dict(mapping) == mapping


def test_col_map_dict_empty_list():
    from flowforge.steps.bulk_load import _col_map_dict
    assert _col_map_dict([]) == {}


def test_col_map_dict_none():
    from flowforge.steps.bulk_load import _col_map_dict
    assert _col_map_dict(None) == {}


def test_col_map_dict_skips_malformed_entries():
    from flowforge.steps.bulk_load import _col_map_dict
    mapping = [
        {'source': 'A', 'target': 'a'},
        {'only_source': 'B'},          # missing 'target' — should be skipped
        'not_a_dict',                  # wrong type — should be skipped
    ]
    result = _col_map_dict(mapping)
    assert result == {'A': 'a'}


# ─── Step-type registration ───────────────────────────────────────────────────

def test_bulk_load_registered_in_loader():
    from flowforge.engine.loader import _STEP_CLASSES
    assert 'bulk_load' in _STEP_CLASSES


def test_bulk_load_valid_step_type_in_api(client, headers):
    """POST /api/pipelines/:id/steps should accept step_type='bulk_load'."""
    pipe_resp = client.post('/api/pipelines',
                            json={'name': 'BulkTypeTest', 'description': ''},
                            headers=headers)
    assert pipe_resp.status_code == 201
    pid = pipe_resp.get_json()['id']

    step_resp = client.post(f'/api/pipelines/{pid}/steps', json={
        'name': 'Load step',
        'step_type': 'bulk_load',
        'step_order': 1,
        'config': {'bulk_load_config_id': ''},
    }, headers=headers)
    assert step_resp.status_code == 201

    client.delete(f'/api/pipelines/{pid}', headers=headers)
