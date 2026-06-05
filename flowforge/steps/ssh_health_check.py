"""SSH health check step — collect standard server metrics and generate a report."""
import logging
import os
from pathlib import Path
from typing import Any

from flowforge.steps.base import BaseStep, StepResult

logger = logging.getLogger(__name__)

_ALL_METRICS = ('load_average', 'memory', 'disk_usage', 'top_processes')


class SshHealthCheckStep(BaseStep):
    """
    Connect to a server via SSH, collect standard health metrics, and generate
    an Excel or CSV report file that can be attached to a downstream email step.

    All four metrics are collected by default. Use the 'metrics' config field
    to collect only specific ones.

    Config fields:
        ssh_connection_id   ID of the SSHConnection row  (required)
        metrics             Metrics to collect — all enabled by default.
                            Choices: load_average, memory, disk_usage, top_processes
        format              Output format: 'excel' | 'csv'  (default: excel)
        output_filename     Filename — supports {{ variables }}
                            Default: ssh_health_{{ current_date }}.<ext>
    """

    step_type = 'ssh_health_check'

    def run(self, context: dict[str, Any]) -> StepResult:
        from flowforge.connections.ssh import get_ssh_connection
        from flowforge.engine.context import render
        from flowforge.reports.health_report import write_health_report

        conn_id = self.config.get('ssh_connection_id')
        if not conn_id:
            return StepResult(success=False, error='ssh_health_check: ssh_connection_id is required')

        metrics = self.config.get('metrics') or list(_ALL_METRICS)
        fmt = self.config.get('format', 'excel').lower()
        ext = 'csv' if fmt == 'csv' else 'xlsx'
        default_filename = f'ssh_health_{{{{ current_date }}}}.{ext}'
        output_filename = render(
            self.config.get('output_filename') or default_filename,
            context,
        )
        output_dir = Path(os.environ.get('FLOWFORGE_OUTPUT_DIR', './output'))
        output_path = output_dir / output_filename

        try:
            conn = get_ssh_connection(conn_id)
            with conn:
                sections = [
                    s for metric in metrics
                    if (s := self._collect(metric, conn.client)) is not None
                ]

            if not sections:
                return StepResult(success=False, error='ssh_health_check: no metrics could be collected')

            write_health_report(sections, output_path, fmt=fmt)

            logs = '\n'.join(f"{s['title']}: {len(s['rows'])} row(s)" for s in sections)
            return StepResult(
                success=True,
                output_path=str(output_path),
                rows_affected=sum(len(s['rows']) for s in sections),
                logs=logs,
            )

        except Exception as exc:
            logger.exception("SSH health check failed")
            return StepResult(success=False, error=f"SSH health check error: {exc}")

    # ── Metric dispatcher ────────────────────────────────────────────────────

    def _collect(self, metric: str, ssh_client) -> dict | None:
        collectors = {
            'load_average':  self._collect_load_average,
            'memory':        self._collect_memory,
            'disk_usage':    self._collect_disk_usage,
            'top_processes': self._collect_top_processes,
        }
        fn = collectors.get(metric)
        if fn is None:
            logger.warning("ssh_health_check: unknown metric '%s' — skipped", metric)
            return None
        try:
            return fn(ssh_client)
        except Exception as exc:
            logger.warning("ssh_health_check: metric '%s' failed: %s", metric, exc)
            return None

    # ── SSH helper ───────────────────────────────────────────────────────────

    def _run_cmd(self, ssh_client, command: str, timeout: int = 30) -> str:
        stdin, stdout, stderr = ssh_client.exec_command(command, timeout=timeout)
        stdin.close()
        output = stdout.read().decode('utf-8', errors='replace').strip()
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            err = stderr.read().decode('utf-8', errors='replace').strip()
            raise RuntimeError(f"exit {exit_code}: {err or output}")
        return output

    # ── Metric collectors ────────────────────────────────────────────────────

    def _collect_load_average(self, ssh_client) -> dict:
        raw = self._run_cmd(ssh_client, 'cat /proc/loadavg && nproc')
        lines = raw.split('\n')
        parts = lines[0].split()
        cpu_count = lines[1].strip() if len(lines) > 1 else 'N/A'
        return {
            'title': 'Load Average',
            'columns': ['Metric', 'Value'],
            'rows': [
                ('1-min Load Average',  parts[0] if len(parts) > 0 else 'N/A'),
                ('5-min Load Average',  parts[1] if len(parts) > 1 else 'N/A'),
                ('15-min Load Average', parts[2] if len(parts) > 2 else 'N/A'),
                ('CPU Count',           cpu_count),
            ],
        }

    def _collect_memory(self, ssh_client) -> dict:
        raw = self._run_cmd(ssh_client, 'free -m')
        rows = []
        for line in raw.split('\n')[1:]:
            parts = line.split()
            if not parts:
                continue
            name = parts[0].rstrip(':').lower()
            if name == 'mem':
                available = parts[6] if len(parts) > 6 else 'N/A'
                rows.append(('Memory', parts[1], parts[2], parts[3], available))
            elif name == 'swap':
                rows.append(('Swap', parts[1], parts[2], parts[3], 'N/A'))
        return {
            'title': 'Memory (MB)',
            'columns': ['Type', 'Total', 'Used', 'Free', 'Available'],
            'rows': rows,
        }

    def _collect_disk_usage(self, ssh_client) -> dict:
        raw = self._run_cmd(ssh_client, 'df -h')
        rows = []
        for line in raw.split('\n')[1:]:
            parts = line.split()
            if len(parts) >= 6:
                rows.append(tuple(parts[:6]))
        return {
            'title': 'Disk Usage',
            'columns': ['Filesystem', 'Size', 'Used', 'Available', 'Use%', 'Mounted On'],
            'rows': rows,
        }

    def _collect_top_processes(self, ssh_client) -> dict:
        raw = self._run_cmd(ssh_client, 'ps aux --sort=-%cpu | head -11')
        rows = []
        for line in raw.split('\n')[1:]:
            parts = line.split(None, 10)
            if len(parts) >= 11:
                rows.append((parts[0], parts[1], parts[2], parts[3], parts[10]))
        return {
            'title': 'Top Processes (CPU)',
            'columns': ['User', 'PID', 'CPU%', 'MEM%', 'Command'],
            'rows': rows,
        }
