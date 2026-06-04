"""Database health check step — collect industry-standard metrics and generate a report."""
import logging
import os
from pathlib import Path
from typing import Any

from flowforge.steps.base import BaseStep, StepResult

logger = logging.getLogger(__name__)


class DbHealthCheckStep(BaseStep):
    """
    Collect health metrics from a configured database connection and generate
    an Excel or CSV report file that can be attached to a downstream email step.
    A text summary is also written to step logs.

    Config fields:
        connection_id     ID of the DbConnection row  (required)
        format            Output format: 'excel' | 'csv'  (default: excel)
        output_filename   Filename — supports {{ variables }}
                          Default: db_health_{{ current_date }}.<ext>
    """

    step_type = 'db_health_check'

    def run(self, context: dict[str, Any]) -> StepResult:
        from flowforge.connections.factory import get_connection
        from flowforge.engine.context import render
        from flowforge.reports.health_report import write_health_report

        conn_id = self.config.get('connection_id')
        if not conn_id:
            return StepResult(success=False, error='db_health_check: connection_id is required')

        fmt = self.config.get('format', 'excel').lower()
        ext = 'csv' if fmt == 'csv' else 'xlsx'
        default_filename = f'db_health_{{{{ current_date }}}}.{ext}'
        output_filename = render(
            self.config.get('output_filename') or default_filename,
            context,
        )
        output_dir = Path(os.environ.get('FLOWFORGE_OUTPUT_DIR', './output'))
        output_path = output_dir / output_filename

        try:
            with get_connection(conn_id) as conn:
                db_type = getattr(conn, 'db_type', None)
                if not db_type:
                    cls_name = conn.__class__.__name__.lower()
                    if 'postgres' in cls_name:
                        db_type = 'postgresql'
                    elif 'oracle' in cls_name:
                        db_type = 'oracle'
                    elif 'mysql' in cls_name:
                        db_type = 'mysql'

                if db_type == 'postgresql':
                    sections, log_summary = self._check_postgres(conn)
                elif db_type == 'oracle':
                    sections, log_summary = self._check_oracle(conn)
                elif db_type == 'mysql':
                    sections, log_summary = self._check_mysql(conn)
                else:
                    return StepResult(
                        success=False,
                        error=f"db_health_check: unsupported database type '{db_type}'",
                    )

            write_health_report(sections, output_path, fmt=fmt)
            return StepResult(
                success=True,
                output_path=str(output_path),
                rows_affected=sum(len(s['rows']) for s in sections),
                logs=log_summary,
            )

        except Exception as exc:
            logger.exception("Database health check failed")
            return StepResult(success=False, error=f"Health check error: {exc}")

    # ── PostgreSQL ───────────────────────────────────────────────────────────

    def _check_postgres(self, conn) -> tuple[list[dict], str]:
        sections: list[dict] = []
        log_lines = ['PostgreSQL Health Check']

        # Active sessions
        active = conn.execute_query(
            "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
        )[0][0]
        sections.append({
            'title': 'Sessions',
            'columns': ['Metric', 'Value'],
            'rows': [('Active Sessions', active)],
        })
        log_lines.append(f'  Active Sessions: {active}')

        # Buffer cache hit ratio
        res = conn.execute_query("""
            SELECT sum(heap_blks_read) AS read, sum(heap_blks_hit) AS hit
            FROM pg_statio_user_tables
        """)
        read, hit = res[0]
        total = (read or 0) + (hit or 0)
        if total > 0:
            ratio = round((hit or 0) / total * 100, 2)
            sections.append({
                'title': 'Cache Performance',
                'columns': ['Metric', 'Value'],
                'rows': [('Cache Hit Ratio %', ratio)],
            })
            log_lines.append(f'  Cache Hit Ratio: {ratio}%')

        # Replication lag
        try:
            lags = conn.execute_query(
                "SELECT client_addr::text, "
                "pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) "
                "FROM pg_stat_replication"
            )
            if lags:
                repl_rows = [(str(r[0]), r[1]) for r in lags if r[1] is not None]
                if repl_rows:
                    sections.append({
                        'title': 'Replication Lag',
                        'columns': ['Replica', 'Lag (bytes)'],
                        'rows': repl_rows,
                    })
                    max_lag = max(r[1] for r in repl_rows)
                    log_lines.append(f'  Max Replication Lag: {max_lag} bytes')
        except Exception:
            pass  # not a primary, or no replicas

        return sections, '\n'.join(log_lines)

    # ── Oracle ───────────────────────────────────────────────────────────────

    def _check_oracle(self, conn) -> tuple[list[dict], str]:
        sections: list[dict] = []
        log_lines = ['Oracle Health Check']

        # Active user sessions
        active = conn.execute_query(
            "SELECT count(*) FROM v$session "
            "WHERE status = 'ACTIVE' AND type != 'BACKGROUND'"
        )[0][0]
        sections.append({
            'title': 'Sessions',
            'columns': ['Metric', 'Value'],
            'rows': [('Active User Sessions', active)],
        })
        log_lines.append(f'  Active User Sessions: {active}')

        # Buffer cache hit ratio
        try:
            ratio = conn.execute_query("""
                SELECT round((1 - (phy.value / NULLIF(cur.value + con.value, 0))) * 100, 2)
                FROM v$sysstat phy, v$sysstat cur, v$sysstat con
                WHERE phy.name = 'physical reads'
                  AND cur.name = 'db block gets'
                  AND con.name = 'consistent gets'
            """)[0][0]
            sections.append({
                'title': 'Buffer Cache',
                'columns': ['Metric', 'Value'],
                'rows': [('Hit Ratio %', ratio)],
            })
            log_lines.append(f'  Buffer Cache Hit Ratio: {ratio}%')
        except Exception:
            pass

        # Tablespace usage (>80%)
        try:
            ts_rows = conn.execute_query("""
                SELECT tablespace_name, round(used_percent, 1)
                FROM dba_tablespace_usage_metrics
                WHERE used_percent > 80
                ORDER BY used_percent DESC
            """)
            if ts_rows:
                sections.append({
                    'title': 'Tablespace Usage (>80%)',
                    'columns': ['Tablespace', 'Used %'],
                    'rows': [(r[0], r[1]) for r in ts_rows],
                })
                log_lines.append(
                    '  High Tablespace: '
                    + ', '.join(f"{r[0]} {r[1]}%" for r in ts_rows)
                )
        except Exception:
            pass

        return sections, '\n'.join(log_lines)

    # ── MySQL ────────────────────────────────────────────────────────────────

    def _check_mysql(self, conn) -> tuple[list[dict], str]:
        sections: list[dict] = []
        log_lines = ['MySQL Health Check']

        threads = conn.execute_query("SHOW STATUS LIKE 'Threads_connected'")
        count = threads[0][1] if threads else 'N/A'
        sections.append({
            'title': 'Threads',
            'columns': ['Metric', 'Value'],
            'rows': [('Connected Threads', count)],
        })
        log_lines.append(f'  Connected Threads: {count}')

        return sections, '\n'.join(log_lines)
