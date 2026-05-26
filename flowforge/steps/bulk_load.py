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
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from flowforge.steps.base import BaseStep, StepResult, validate_identifier

logger = logging.getLogger(__name__)


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

    if not connection_id:
        return None, StepResult(success=False, error='bulk_load: connection_id is required')
    if not source_dir:
        return None, StepResult(success=False, error='bulk_load: source_directory is required')
    if not target_table:
        return None, StepResult(success=False, error='bulk_load: target_table is required')
    if len(delimiter) != 1 or not delimiter.isprintable() or delimiter in ("'", '"', '\\'):
        return None, StepResult(
            success=False,
            error=f"bulk_load: invalid delimiter {delimiter!r} — must be a single printable non-quote character",
        )
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
    from flowforge.db.models import DbConnection as DbConnectionModel, db

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

        data_rows = all_rows[header_rows:]
        if footer_rows:
            data_rows = data_rows[:-footer_rows]

        if not data_rows:
            return 0, 0, 'No data rows after stripping header/footer.'

        if header_rows >= 1 and all_rows:
            raw_cols = [c.strip() for c in all_rows[0]]
            cols = [col_map.get(c, c) for c in raw_cols]
            for col in cols:
                validate_identifier(col, 'column name')
        else:
            cols = [f'col{i}' for i in range(len(data_rows[0]))]

        if load_mode == 'replace':
            cur.execute(f'TRUNCATE TABLE {target_table}')  # nosec B608
            db_conn.commit()

        placeholders = ', '.join(['%s'] * len(cols))
        col_names    = ', '.join(cols)
        sql = f'INSERT INTO {target_table} ({col_names}) VALUES ({placeholders})'  # nosec B608

        CHUNK = 10_000
        records_loaded = 0
        records_failed = 0
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

        if header_rows >= 1 and all_lines:
            raw_header = next(csv.reader([all_lines[0]], delimiter=delimiter))
            mapped_header = [col_map.get(c.strip(), c.strip()) for c in raw_header]
            for col in mapped_header:
                validate_identifier(col, 'column name')
        else:
            mapped_header = None

        data_lines = all_lines[header_rows:]
        if footer_rows:
            data_lines = data_lines[:-footer_rows]

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

    if header_rows >= 1 and all_rows:
        raw_cols    = [c.strip() for c in all_rows[0]]
        target_cols = [col_map.get(c, c) for c in raw_cols]
    else:
        target_cols = []

    data_rows = all_rows[header_rows:]
    if footer_rows:
        data_rows = data_rows[:-footer_rows]

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
        password = conn_cfg.get('password', '')
        host     = conn_cfg.get('host', 'localhost')
        port     = conn_cfg.get('port', 1521)
        service  = conn_cfg.get('service_name') or conn_cfg.get('database', '')
        dsn      = f'{host}:{port}/{service}'

        par_file = tmpdir / 'load.par'
        par_file.write_text(
            f'userid={user}/{password}@{dsn}\n'
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
        subprocess.run(cmd, capture_output=True, text=True, timeout=3600)

        log_text = log_file.read_text(errors='replace') if log_file.exists() else ''
        records_loaded, records_failed = _parse_sqlldr_counts(log_text)
        bad_content = _read_bad_file(bad_file)
        summary = f'SQL*Loader: {records_loaded} loaded, {records_failed} failed\n{log_text}{bad_content}'
        return records_loaded, records_failed, summary
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ─── Archive helper ────────────────────────────────────────────────────────────

def _archive_file(file_path: Path, archive_dir: str) -> None:
    dest = Path(archive_dir)
    dest.mkdir(parents=True, exist_ok=True)
    shutil.move(str(file_path), dest / file_path.name)
    logger.debug('Archived %s → %s', file_path.name, dest)
