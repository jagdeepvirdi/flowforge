"""Bulk-load step — directory-scan + multi-path loader.

Execution paths (in order of preference):
  1. Oracle + use_sqlloader=true → subprocess sqlldr + auto-generated .ctl file
  2. PostgreSQL → psycopg2 copy_expert (COPY FROM STDIN)
  3. Python fallback (any DB) → chunked executemany, no external tools required
"""
import csv
import io
import logging
import shutil
import subprocess  # nosec B404 — only used with a fixed arg list, no shell=True (see call site)
import tempfile
import time
from pathlib import Path
from typing import Any

from flowforge.steps.base import BaseStep, StepResult, validate_identifier

logger = logging.getLogger(__name__)


# ─── Shared validation / extraction helpers ────────────────────────────────────

def _validate_bulk_cfg(connection_id: str, source_dir: str, target_table: str, delimiter: str) -> str | None:
    """Return an error message if any required field is invalid, else None."""
    if not connection_id:
        return 'bulk_load: connection_id is required'
    if not source_dir:
        return 'bulk_load: source_directory is required'
    if not target_table:
        return 'bulk_load: target_table is required'
    if len(delimiter) != 1 or not delimiter.isprintable() or delimiter in ("'", '"', '\\'):
        return (
            f"bulk_load: invalid delimiter {delimiter!r} — "
            "must be a single printable non-quote character"
        )
    return None


def _extract_data_rows(all_rows: list, header_rows: int, footer_rows: int) -> list:
    """Slice header and optional footer rows from a list of CSV rows or text lines."""
    data = all_rows[header_rows:]
    return data[:-footer_rows] if footer_rows else data


def _derive_csv_columns(
    all_rows: list,
    header_rows: int,
    col_map: dict[str, str],
    *,
    validate: bool = True,
) -> list[str]:
    """Return target column names from the CSV header row, or [] if no header.

    When validate=True (default) each column name is checked with validate_identifier.
    Pass validate=False for SQL*Loader paths where the DB engine validates instead.
    """
    if not (header_rows >= 1 and all_rows):
        return []
    raw_cols = [c.strip() for c in all_rows[0]]
    cols = [col_map.get(c, c) for c in raw_cols]
    if validate:
        for col in cols:
            validate_identifier(col, 'column name')
    return cols


def _derive_line_columns(
    lines: list[str],
    header_rows: int,
    col_map: dict[str, str],
    delimiter: str,
) -> list[str] | None:
    """Parse the first text line as column headers for COPY FROM STDIN.

    Returns None if header_rows < 1 (no header → COPY uses table column order).
    """
    if header_rows < 1 or not lines:
        return None
    raw_header = next(csv.reader([lines[0]], delimiter=delimiter))
    mapped = [col_map.get(c.strip(), c.strip()) for c in raw_header]
    for col in mapped:
        validate_identifier(col, 'column name')
    return mapped


# ─── Config resolution ─────────────────────────────────────────────────────────

def _resolve_run_config(step_cfg: dict, context: dict, render) -> tuple[dict | None, StepResult | None]:
    """Resolve and validate bulk-load config. Returns (cfg, None) or (None, error_result)."""
    bulk_load_config_id = step_cfg.get('bulk_load_config_id', '')
    if bulk_load_config_id:
        cfg = _load_bulk_load_config(bulk_load_config_id)
        if cfg is None:
            return None, StepResult(success=False, error=f'bulk_load: config not found: {bulk_load_config_id}')
    else:
        cfg = step_cfg

    connection_id   = cfg.get('connection_id', '')
    source_dir      = render(cfg.get('source_directory', ''), context)
    target_table    = render(cfg.get('target_table', ''), context)
    delimiter       = cfg.get('delimiter', ',')
    archive_dir_tpl = cfg.get('archive_directory', '') or ''

    cfg_err = _validate_bulk_cfg(connection_id, source_dir, target_table, delimiter)
    if cfg_err:
        return None, StepResult(success=False, error=cfg_err)

    try:
        validate_identifier(target_table, 'target_table')
    except ValueError as e:
        return None, StepResult(success=False, error=f'bulk_load: {e}')

    return {
        'connection_id':       connection_id,
        'source_dir':          source_dir,
        'file_prefix':         cfg.get('file_prefix', '') or '',
        'file_prefix_exclude': cfg.get('file_prefix_exclude', '') or '',
        'file_type':           cfg.get('file_type', 'csv').lower().lstrip('.'),
        'delimiter':           delimiter,
        'header_rows':         int(cfg.get('header_rows', 1)),
        'footer_rows':         int(cfg.get('footer_rows', 0)),
        'target_table':        target_table,
        'load_mode':           cfg.get('load_mode', 'append'),
        'column_mapping':      cfg.get('column_mapping') or [],
        'use_sqlloader':       bool(cfg.get('use_sqlloader', False)),
        'archive_dir':         render(archive_dir_tpl, context) if archive_dir_tpl else '',
        'on_no_files':         cfg.get('on_no_files', 'skip'),
    }, None


def _handle_no_files(source_dir: str, file_prefix: str, ext: str, on_no_files: str) -> StepResult:
    msg = f'bulk_load: no files found in {source_dir} matching prefix={file_prefix!r} ext={ext!r}'
    if on_no_files == 'skip':
        logger.info('%s — skipping (on_no_files=skip)', msg)
        return StepResult(
            success=True, logs=msg + ' — skipped.',
            files_found=0, files_loaded=0, files_failed=0,
            records_loaded=0, records_failed=0, duration_sec=0.0,
        )
    return StepResult(success=False, error=msg)


def _dispatch_single_file(
    db_type: str,
    use_sqlloader: bool,
    conn_cfg: dict,
    file_path: Path,
    delimiter: str,
    header_rows: int,
    footer_rows: int,
    target_table: str,
    load_mode: str,
    column_mapping,
) -> tuple[int, int, str]:
    if db_type == 'oracle' and use_sqlloader:
        return _load_sqlloader(conn_cfg, file_path, delimiter, header_rows, footer_rows, target_table, load_mode, column_mapping)
    if db_type == 'postgresql':
        return _load_postgres_copy(conn_cfg, file_path, delimiter, header_rows, footer_rows, target_table, load_mode, column_mapping)
    return _load_python_fallback(conn_cfg, file_path, delimiter, header_rows, footer_rows, target_table, load_mode, column_mapping)


class BulkLoadStep(BaseStep):
    step_type = 'bulk_load'

    def run(self, context: dict[str, Any]) -> StepResult:
        from flowforge.engine.context import render

        cfg, err = _resolve_run_config(self.config, context, render)
        if err:
            return err

        src_path = Path(cfg['source_dir'])
        if not src_path.is_dir():
            return StepResult(success=False, error=f"bulk_load: source_directory not found: {cfg['source_dir']}")

        ext = f".{cfg['file_type']}"
        files = sorted(
            f for f in src_path.iterdir()
            if f.is_file()
            and f.suffix.lower() == ext
            and (not cfg['file_prefix'] or f.name.startswith(cfg['file_prefix']))
            and (not cfg['file_prefix_exclude'] or not f.name.startswith(cfg['file_prefix_exclude']))
        )
        files_found = len(files)

        if files_found == 0:
            return _handle_no_files(cfg['source_dir'], cfg['file_prefix'], ext, cfg['on_no_files'])

        try:
            conn_cfg = _resolve_connection(cfg['connection_id'])
        except Exception as e:
            return StepResult(success=False, error=f'bulk_load: could not open connection: {e}')

        db_type = conn_cfg.get('_db_type', 'postgresql')
        t_start = time.monotonic()
        files_loaded = files_failed = total_records_loaded = total_records_failed = 0
        log_lines: list[str] = []

        for file_path in files:
            try:
                loaded, failed, file_log = _dispatch_single_file(
                    db_type, cfg['use_sqlloader'], conn_cfg, file_path,
                    cfg['delimiter'], cfg['header_rows'], cfg['footer_rows'],
                    cfg['target_table'], cfg['load_mode'], cfg['column_mapping'],
                )
                total_records_loaded += loaded
                total_records_failed += failed
                log_lines.append(f'[OK]  {file_path.name}: {loaded} loaded, {failed} failed\n{file_log}')
                files_loaded += 1
                if cfg['archive_dir']:
                    _archive_file(file_path, cfg['archive_dir'])
            except Exception as e:
                files_failed += 1
                logger.exception('bulk_load: error loading %s', file_path.name)
                log_lines.append(f'[ERR] {file_path.name}: {e}')

        duration_sec = round(time.monotonic() - t_start, 2)
        summary = (
            f'bulk_load: {files_found} found, {files_loaded} loaded, {files_failed} failed — '
            f'{total_records_loaded} records loaded, {total_records_failed} failed — '
            f'{duration_sec}s'
        )
        logger.info(summary)
        success = files_failed == 0
        return StepResult(
            success=success,
            rows_affected=total_records_loaded,
            logs=summary + '\n\n' + '\n'.join(log_lines),
            error='' if success else f'{files_failed} file(s) failed to load',
            files_found=files_found,
            files_loaded=files_loaded,
            files_failed=files_failed,
            records_loaded=total_records_loaded,
            records_failed=total_records_failed,
            duration_sec=duration_sec,
        )


# ─── Config loader ────────────────────────────────────────────────────────────

def _load_bulk_load_config(config_id: str) -> dict | None:
    """Load a BulkLoadConfig row and return it as a plain dict for the runner."""
    from flowforge.db.models import BulkLoadConfig, db
    row = db.session.get(BulkLoadConfig, config_id)
    if not row:
        return None
    return {
        'connection_id':       row.connection_id or '',
        'source_directory':    row.source_directory or '',
        'file_prefix':         row.file_prefix or '',
        'file_prefix_exclude': row.file_prefix_exclude or '',
        'file_type':           row.file_type or 'csv',
        'delimiter':           row.delimiter or ',',
        'header_rows':         row.header_rows if row.header_rows is not None else 1,
        'footer_rows':         row.footer_rows if row.footer_rows is not None else 0,
        'target_table':        row.target_table or '',
        'load_mode':           row.load_mode or 'append',
        'column_mapping':      row.column_mapping or [],
        'use_sqlloader':       bool(row.use_sqlloader),
        'archive_directory':   row.archive_directory or '',
        'on_no_files':         row.on_no_files or 'skip',
    }


# ─── Connection helpers ────────────────────────────────────────────────────────

def _resolve_connection(connection_id: str) -> dict:
    from flowforge.crypto import decrypt_config
    from flowforge.db.models import DbConnection as DbConnectionModel
    from flowforge.db.models import db

    row = db.session.get(DbConnectionModel, connection_id)
    if not row:
        raise ValueError(f'DB connection not found: {connection_id}')

    config = decrypt_config(row.config)
    config['_db_type'] = row.db_type
    return config


def _open_raw_connection(conn_cfg: dict):
    db_type = conn_cfg.get('_db_type', 'postgresql')
    if db_type == 'postgresql':
        import psycopg2
        return psycopg2.connect(
            host=conn_cfg.get('host', 'localhost'),
            port=int(conn_cfg.get('port', 5432)),
            dbname=conn_cfg.get('database', ''),
            user=conn_cfg.get('username', ''),
            password=conn_cfg.get('password', ''),
        )
    if db_type == 'oracle':
        import oracledb
        service = conn_cfg.get('service_name') or conn_cfg.get('database', '')
        return oracledb.connect(
            user=conn_cfg.get('username', ''),
            password=conn_cfg.get('password', ''),
            dsn=f"{conn_cfg.get('host', 'localhost')}:{conn_cfg.get('port', 1521)}/{service}",
        )
    raise ValueError(f'Unsupported db_type for bulk_load: {db_type}')


def _col_map_dict(column_mapping) -> dict[str, str]:
    if isinstance(column_mapping, list):
        return {
            entry['source']: entry['target']
            for entry in column_mapping
            if isinstance(entry, dict) and 'source' in entry and 'target' in entry
        }
    if isinstance(column_mapping, dict):
        return column_mapping
    return {}


# ─── Python fallback (any DB) ─────────────────────────────────────────────────

def _load_python_fallback(
    conn_cfg: dict,
    file_path: Path,
    delimiter: str,
    header_rows: int,
    footer_rows: int,
    target_table: str,
    load_mode: str,
    column_mapping,
) -> tuple[int, int, str]:
    col_map = _col_map_dict(column_mapping)
    db_conn = _open_raw_connection(conn_cfg)
    try:
        cur = db_conn.cursor()
        with open(file_path, newline='', encoding='utf-8-sig') as fh:
            all_rows = list(csv.reader(fh, delimiter=delimiter))

        data_rows = _extract_data_rows(all_rows, header_rows, footer_rows)
        if not data_rows:
            return 0, 0, 'No data rows after stripping header/footer.'

        derived = _derive_csv_columns(all_rows, header_rows, col_map)
        cols = derived or [f'col{i}' for i in range(len(data_rows[0]))]

        if load_mode == 'replace':
            cur.execute(f'TRUNCATE TABLE {target_table}')  # nosec B608
            db_conn.commit()

        placeholders = ', '.join(['%s'] * len(cols))
        col_names    = ', '.join(cols)
        sql = f'INSERT INTO {target_table} ({col_names}) VALUES ({placeholders})'  # nosec B608

        CHUNK = 10_000
        records_loaded = records_failed = 0
        log_parts: list[str] = []

        for i in range(0, len(data_rows), CHUNK):
            chunk = data_rows[i:i + CHUNK]
            try:
                cur.executemany(sql, chunk)
                db_conn.commit()
                records_loaded += len(chunk)
            except Exception as e:
                db_conn.rollback()
                records_failed += len(chunk)
                log_parts.append(f'Chunk {i // CHUNK + 1} failed: {e}')

        cur.close()
        summary = f'Python fallback: {records_loaded} loaded, {records_failed} failed'
        if log_parts:
            summary += '\n' + '\n'.join(log_parts)
        return records_loaded, records_failed, summary
    finally:
        db_conn.close()


# ─── PostgreSQL COPY FROM STDIN ────────────────────────────────────────────────

def _load_postgres_copy(
    conn_cfg: dict,
    file_path: Path,
    delimiter: str,
    header_rows: int,
    footer_rows: int,
    target_table: str,
    load_mode: str,
    column_mapping,
) -> tuple[int, int, str]:
    col_map = _col_map_dict(column_mapping)
    db_conn = _open_raw_connection(conn_cfg)
    try:
        cur = db_conn.cursor()

        with open(file_path, newline='', encoding='utf-8-sig') as fh:
            all_lines = fh.readlines()

        mapped_header = _derive_line_columns(all_lines, header_rows, col_map, delimiter)
        data_lines = _extract_data_rows(all_lines, header_rows, footer_rows)

        if load_mode == 'replace':
            cur.execute(f'TRUNCATE TABLE {target_table}')  # nosec B608
            db_conn.commit()

        data_io = io.StringIO(''.join(data_lines))
        col_clause = f'({", ".join(mapped_header)})' if mapped_header else ''
        copy_sql = (
            f"COPY {target_table} {col_clause} FROM STDIN "
            f"WITH (FORMAT CSV, DELIMITER '{delimiter}')"
        )
        cur.copy_expert(copy_sql, data_io)
        records_loaded = cur.rowcount if cur.rowcount >= 0 else len(data_lines)
        db_conn.commit()
        cur.close()

        return records_loaded, 0, f'PostgreSQL COPY: {records_loaded} rows loaded'
    except Exception:
        db_conn.rollback()
        raise
    finally:
        db_conn.close()


# ─── Oracle SQL*Loader ─────────────────────────────────────────────────────────

def _parse_sqlldr_counts(log_text: str) -> tuple[int, int]:
    """Extract loaded/failed row counts from a SQL*Loader log."""
    loaded = failed = 0
    for line in log_text.splitlines():
        low = line.lower()
        if 'rows successfully loaded' in low or 'row successfully loaded' in low:
            for tok in line.split():
                if tok.isdigit():
                    loaded = int(tok)
                    break
        if 'rows not loaded due to data errors' in low:
            for tok in line.split():
                if tok.isdigit():
                    failed = int(tok)
                    break
    return loaded, failed


def _read_bad_file(bad_file: Path) -> str:
    if not bad_file.exists() or bad_file.stat().st_size == 0:
        return ''
    with open(bad_file, encoding='utf-8', errors='replace') as bf:
        bad_lines = bf.readlines()[:50]
    return '\nRejected rows (.bad, first 50):\n' + ''.join(bad_lines)


def _load_sqlloader(
    conn_cfg: dict,
    file_path: Path,
    delimiter: str,
    header_rows: int,
    footer_rows: int,
    target_table: str,
    load_mode: str,
    column_mapping,
) -> tuple[int, int, str]:
    col_map = _col_map_dict(column_mapping)

    with open(file_path, newline='', encoding='utf-8-sig') as fh:
        all_rows = list(csv.reader(fh, delimiter=delimiter))

    target_cols = _derive_csv_columns(all_rows, header_rows, col_map, validate=False)
    data_rows = _extract_data_rows(all_rows, header_rows, footer_rows)

    tmpdir = Path(tempfile.mkdtemp(prefix='flowforge_sqlldr_'))
    try:
        data_file = tmpdir / 'data.csv'
        ctl_file  = tmpdir / 'load.ctl'
        log_file  = tmpdir / 'load.log'
        bad_file  = tmpdir / 'load.bad'

        with open(data_file, 'w', newline='', encoding='utf-8') as fh:
            csv.writer(fh, delimiter=delimiter).writerows(data_rows)

        sqlldr_mode = 'APPEND' if load_mode == 'append' else 'TRUNCATE'
        col_spec    = ', '.join(target_cols)
        ctl_file.write_text(
            f"LOAD DATA\n"
            f"INFILE '{data_file}'\n"
            f"{sqlldr_mode}\n"
            f"INTO TABLE {target_table}\n"
            f"FIELDS TERMINATED BY '{delimiter}' OPTIONALLY ENCLOSED BY '\"'\n"
            f"TRAILING NULLCOLS\n"
            f"({col_spec})\n"
        )

        user     = conn_cfg.get('username', '')
        pwd = conn_cfg.get('password', '')
        host     = conn_cfg.get('host', 'localhost')
        port     = conn_cfg.get('port', 1521)
        service  = conn_cfg.get('service_name') or conn_cfg.get('database', '')
        dsn      = f'{host}:{port}/{service}'

        par_file = tmpdir / 'load.par'
        par_file.write_text(
            f'userid={user}/{pwd}@{dsn}\n'
            f'control={ctl_file}\n'
            f'log={log_file}\n'
            f'bad={bad_file}\n'
            'silent=header,feedback\n',
            encoding='utf-8',
        )
        try:
            par_file.chmod(0o600)
        except NotImplementedError:
            pass  # Windows; tmpdir is already process-private

        cmd = ['sqlldr', f'parfile={par_file}']
        subprocess.run(cmd, capture_output=True, text=True, timeout=3600)  # nosec B603 — fixed arg list, no shell, par_file is app-controlled

        log_text = log_file.read_text(errors='replace') if log_file.exists() else ''
        records_loaded, records_failed = _parse_sqlldr_counts(log_text)
        bad_content = _read_bad_file(bad_file)
        summary = f'SQL*Loader: {records_loaded} loaded, {records_failed} failed\n{log_text}{bad_content}'
        return records_loaded, records_failed, summary
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ─── Preview / validate (no data touched unless dry_run=True, always rolled back) ──

_PG_SQLSTATE_TYPES = {
    '23502': 'not_null_violation',
    '23505': 'unique_violation',
    '23503': 'foreign_key_violation',
    '23514': 'check_violation',
    '22001': 'value_too_long',
}

_ORA_CODE_TYPES = {
    '01400': 'not_null_violation',
    '00001': 'unique_violation',
    '02291': 'foreign_key_violation',
    '12899': 'value_too_long',
    '01722': 'invalid_type',
    '01858': 'invalid_type',
}


def _classify_insert_error(exc: Exception) -> tuple[str, str | None]:
    """Best-effort (error_type, column_name) from a driver exception.

    Prefers psycopg2's structured `.diag` fields (exact SQLSTATE + column
    name) when available, and falls back to substring/ORA-code matching on
    the message for Oracle and any other driver.
    """
    diag = getattr(exc, 'diag', None)
    if diag is not None:
        sqlstate = getattr(diag, 'sqlstate', None)
        column = getattr(diag, 'column_name', None)
        if sqlstate in _PG_SQLSTATE_TYPES:
            return _PG_SQLSTATE_TYPES[sqlstate], column
        if sqlstate and sqlstate.startswith('22'):
            return 'invalid_type', column
        if sqlstate and sqlstate.startswith('23'):
            return 'constraint_violation', column
        return 'db_error', column

    msg = str(exc)
    for code, err_type in _ORA_CODE_TYPES.items():
        if f'ORA-{code}' in msg:
            return err_type, None

    low = msg.lower()
    if 'not-null' in low or 'not null' in low or 'null value' in low:
        return 'not_null_violation', None
    if 'unique' in low or 'duplicate key' in low:
        return 'unique_violation', None
    if 'too long' in low or 'value too large' in low:
        return 'value_too_long', None
    if 'invalid input syntax' in low or 'invalid number' in low or 'invalid literal' in low:
        return 'invalid_type', None
    return 'db_error', None


def _dry_run_insert_rows(
    conn_cfg: dict,
    target_table: str,
    columns: list[str],
    sample_rows: list[list[str]],
) -> list[dict]:
    """Attempt each sample row as a real INSERT against the real target table,
    one row per SAVEPOINT, then roll the whole transaction back — nothing is
    ever committed.

    Reuses the exact INSERT statement `_load_python_fallback` builds for a
    real load, so a NOT NULL / unique / length / type error surfaced here is
    the same error a real run would hit, not a heuristic re-implementation.

    Rows are tried individually (unlike the real load's executemany/COPY
    batching) so a systemic failure on one row doesn't abort the whole batch
    before an unrelated failure on another row can be found — batched
    execution stops at the first bad row.

    Returns a list of per-row failures: [{row_index, column, error_type,
    message}, ...] for only the rows that failed.
    """
    if not columns or not sample_rows:
        return []

    placeholders = ', '.join(['%s'] * len(columns))
    col_names = ', '.join(columns)
    sql = f'INSERT INTO {target_table} ({col_names}) VALUES ({placeholders})'  # nosec B608

    db_conn = _open_raw_connection(conn_cfg)
    row_errors: list[dict] = []
    try:
        cur = db_conn.cursor()
        for idx, row in enumerate(sample_rows):
            cur.execute('SAVEPOINT ff_dry_run_row')
            try:
                cur.execute(sql, row)
            except Exception as e:
                cur.execute('ROLLBACK TO SAVEPOINT ff_dry_run_row')
                error_type, column = _classify_insert_error(e)
                row_errors.append({
                    'row_index': idx,
                    'column': column,
                    'error_type': error_type,
                    'message': str(e).strip(),
                })
            else:
                cur.execute('RELEASE SAVEPOINT ff_dry_run_row')
        cur.close()
    finally:
        db_conn.rollback()
        db_conn.close()
    return row_errors


def _group_insert_errors(row_errors: list[dict]) -> list[dict]:
    """Group per-row failures by (column, error_type) signature so a systemic
    issue (e.g. a batch of blanks hitting one NOT NULL column) reports as one
    entry with a row count, instead of a dozen near-duplicate messages."""
    groups: dict[tuple[str | None, str], dict] = {}
    order: list[tuple[str | None, str]] = []
    for err in row_errors:
        key = (err['column'], err['error_type'])
        if key not in groups:
            groups[key] = {
                'column':      err['column'],
                'error_type':  err['error_type'],
                'message':     err['message'],
                'row_indices': [],
            }
            order.append(key)
        groups[key]['row_indices'].append(err['row_index'])

    result = [groups[k] for k in order]
    for g in result:
        g['count'] = len(g['row_indices'])
    result.sort(key=lambda g: -g['count'])
    return result


def _insert_error_summary(row_errors: list[dict], total_sampled: int) -> str:
    if not row_errors:
        return ''
    n_types = len({(e['column'], e['error_type']) for e in row_errors})
    n_rows = len({e['row_index'] for e in row_errors})
    type_word = 'error type' if n_types == 1 else 'error types'
    return f'{n_types} {type_word} across {n_rows} of {total_sampled} sampled rows'


def _fetch_table_columns(connection_id: str, target_table: str) -> set[str] | None:
    """Return lower-cased column names for target_table, or None if it doesn't exist."""
    from flowforge.connections.factory import get_connection

    clean  = target_table.replace('"', '')
    parts  = clean.split('.')
    tname  = parts[-1]
    schema = parts[0] if len(parts) > 1 else None

    with get_connection(connection_id) as conn:
        db_type = getattr(conn, 'db_type', 'postgresql')
        if db_type == 'oracle':
            if schema:
                rows = conn.execute_query(
                    "SELECT column_name FROM all_tab_columns WHERE table_name = UPPER(:1) AND owner = UPPER(:2)",
                    (tname, schema),
                )
            else:
                rows = conn.execute_query(
                    "SELECT column_name FROM user_tab_columns WHERE table_name = UPPER(:1)",
                    (tname,),
                )
        else:  # postgresql (and generic fallback)
            rows = conn.execute_query(
                "SELECT column_name FROM information_schema.columns WHERE table_name = %s AND table_schema = %s",
                (tname, schema or 'public'),
            )
    if not rows:
        return None
    return {str(r[0]).lower() for r in rows}


def preview_bulk_load(cfg: dict, context: dict | None = None, dry_run: bool = False) -> dict:
    """Preview the first matching file for a bulk-load config without loading any data.

    When dry_run=True and the target table exists with matching columns, also
    attempts a real (rolled-back) INSERT of each sampled row to catch
    type-coercion and constraint errors (NOT NULL, unique/PK, length
    overflow) that untyped CSV text can't reveal on its own — see
    _dry_run_insert_rows(). Not available for the Oracle SQL*Loader path
    (sqlldr manages its own commits); file/header/column checks still run.

    Returns {file_name, files_matched, columns, sample_rows, row_count_sampled,
    warnings, error_groups, insert_error_summary}.
    Raises ValueError on hard-stop conditions (bad directory, no matching files, bad delimiter).
    """
    from flowforge.engine.context import build, render

    ctx = context if context is not None else build('preview')

    # Keep the original (unrendered) template strings around for user-facing
    # messages — never echo the *rendered* value back to the caller. A crafted
    # template (e.g. '{{ env.SOME_CREDENTIAL }}') would otherwise let its
    # resolved value leak straight into an HTTP error/warning response.
    source_dir_tpl = cfg.get('source_directory', '')
    target_table_tpl = cfg.get('target_table', '')

    source_dir = render(source_dir_tpl, ctx)
    if not source_dir:
        raise ValueError('source_directory is required')

    src_path = Path(source_dir)
    if not src_path.is_dir():
        raise ValueError(f'source_directory not found: {source_dir_tpl}')

    file_type           = (cfg.get('file_type') or 'csv').lower().lstrip('.')
    file_prefix         = cfg.get('file_prefix') or ''
    file_prefix_exclude = cfg.get('file_prefix_exclude') or ''
    delimiter           = cfg.get('delimiter') or ','
    header_rows         = int(cfg.get('header_rows', 1))
    footer_rows         = int(cfg.get('footer_rows', 0))
    target_table        = render(target_table_tpl, ctx)
    col_map             = _col_map_dict(cfg.get('column_mapping') or [])

    if len(delimiter) != 1 or not delimiter.isprintable() or delimiter in ("'", '"', '\\'):
        raise ValueError(f"invalid delimiter {delimiter!r} — must be a single printable non-quote character")

    ext = f'.{file_type}'
    files = sorted(
        f for f in src_path.iterdir()
        if f.is_file()
        and f.suffix.lower() == ext
        and (not file_prefix or f.name.startswith(file_prefix))
        and (not file_prefix_exclude or not f.name.startswith(file_prefix_exclude))
    )
    if not files:
        raise ValueError(f'no files found in {source_dir_tpl} matching prefix={file_prefix!r} ext={ext!r}')

    file_path = files[0]
    warnings: list[str] = []
    if len(files) > 1:
        warnings.append(
            f'{len(files)} files match — previewing the first one alphabetically ({file_path.name}); '
            'the real run will load all of them.'
        )

    try:
        with open(file_path, newline='', encoding='utf-8-sig') as fh:
            all_rows = list(csv.reader(fh, delimiter=delimiter))
    except UnicodeDecodeError as e:
        raise ValueError(f'could not read {file_path.name} as UTF-8: {e}') from e

    if len(all_rows) <= header_rows + footer_rows:
        raise ValueError(
            f'{file_path.name} has no data rows after stripping {header_rows} header + {footer_rows} footer row(s)'
        )

    try:
        columns = _derive_csv_columns(all_rows, header_rows, col_map)
    except ValueError as e:
        raise ValueError(f'{file_path.name}: {e}') from e

    data_rows = _extract_data_rows(all_rows, header_rows, footer_rows)
    if not columns:
        columns = [f'col{i}' for i in range(len(data_rows[0]))]

    SAMPLE_ROWS = 20
    sample_rows = data_rows[:SAMPLE_ROWS]

    ragged_lengths = {len(r) for r in data_rows if len(r) != len(columns)}
    if ragged_lengths:
        warnings.append(
            f'{len(columns)} column(s) parsed from the header, but some data rows have a different '
            f'field count (e.g. {sorted(ragged_lengths)[0]}) — double-check the delimiter.'
        )

    connection_id = cfg.get('connection_id') or ''
    row_errors: list[dict] = []
    if not target_table:
        warnings.append('target_table not set — skipping target-table column check.')
    elif not connection_id:
        warnings.append('No connection selected — skipping target-table column check.')
    else:
        try:
            validate_identifier(target_table, 'target_table')
        except ValueError:
            warnings.append(
                f"Invalid target_table {target_table_tpl!r}: only letters, digits, underscores, and dots allowed"
            )
        else:
            try:
                target_cols = _fetch_table_columns(connection_id, target_table)
                if target_cols is None:
                    warnings.append(f'Target table {target_table_tpl!r} does not exist (or is not visible to this connection).')
                else:
                    missing = [c for c in columns if c.lower() not in target_cols]
                    if missing:
                        warnings.append(f"Column(s) not found in {target_table_tpl}: {', '.join(missing)}")
                    elif dry_run:
                        try:
                            conn_cfg = _resolve_connection(connection_id)
                        except Exception as e:
                            warnings.append(f'Could not open connection for dry-run insert test: {type(e).__name__}: {e}')
                        else:
                            db_type = conn_cfg.get('_db_type', 'postgresql')
                            if db_type == 'oracle' and bool(cfg.get('use_sqlloader', False)):
                                warnings.append(
                                    'Dry-run insert testing is not available for the SQL*Loader path '
                                    '(sqlldr manages its own commits) — only file, header, and column checks were run.'
                                )
                            else:
                                try:
                                    row_errors = _dry_run_insert_rows(conn_cfg, target_table, columns, sample_rows)
                                except Exception as e:
                                    warnings.append(f'Could not run dry-run insert test: {type(e).__name__}: {e}')
            except Exception as e:
                warnings.append(f'Could not verify target table columns: {type(e).__name__}: {e}')

    return {
        'file_name':            file_path.name,
        'files_matched':        len(files),
        'columns':              columns,
        'sample_rows':          sample_rows,
        'row_count_sampled':    len(sample_rows),
        'warnings':             warnings,
        'error_groups':         _group_insert_errors(row_errors),
        'insert_error_summary': _insert_error_summary(row_errors, len(sample_rows)),
    }


# ─── Archive helper ────────────────────────────────────────────────────────────

def _archive_file(file_path: Path, archive_dir: str) -> None:
    dest = Path(archive_dir)
    dest.mkdir(parents=True, exist_ok=True)
    shutil.move(str(file_path), dest / file_path.name)
    logger.debug('Archived %s → %s', file_path.name, dest)
