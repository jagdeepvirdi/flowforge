"""SSH command step — execute remote commands or scripts via paramiko."""
import logging
import os
from pathlib import Path
from typing import Any

from flowforge.steps.base import BaseStep, StepResult

logger = logging.getLogger(__name__)


class SshCommandStep(BaseStep):
    """Execute remote commands or scripts via SSH.

    Config fields:
        ssh_connection_id   ID of the SSHConnection row  (required)
        command             Command to execute — supports {{ variables }}  (required)
        timeout             Command execution timeout in seconds  (default: 60)
        capture_output      Include stdout/stderr in Run History logs (default: true)
        output_var          Pipeline variable to store stdout in (optional)
        save_output         Save stdout to a file and set output_path (default: false)
        output_filename     Filename for the saved output — supports {{ variables }}
                            Default: ssh_output_{{ current_date }}.log
        include_stderr      Append stderr to the saved file (default: true)
    """

    step_type = 'ssh_command'

    def run(self, context: dict[str, Any]) -> StepResult:
        from flowforge.connections.ssh import get_ssh_connection
        from flowforge.engine.context import render

        conn_id = self.config.get('ssh_connection_id')
        if not conn_id:
            return StepResult(success=False, error='ssh_command: ssh_connection_id is required')

        command = render(self.config.get('command', ''), context).strip()
        if not command:
            return StepResult(success=False, error='ssh_command: command is required')

        timeout        = int(self.config.get('timeout', 60))
        capture        = bool(self.config.get('capture_output', True))
        output_var     = self.config.get('output_var')
        save_output    = bool(self.config.get('save_output', False))
        include_stderr = bool(self.config.get('include_stderr', True))

        try:
            conn = get_ssh_connection(conn_id)
            with conn:
                logger.info("SSH: executing command on %s: %s", conn.host, command)

                stdin, stdout, stderr = conn.client.exec_command(command, timeout=timeout)
                stdin.close()

                out_text   = stdout.read().decode('utf-8', errors='replace').strip()
                err_text   = stderr.read().decode('utf-8', errors='replace').strip()
                exit_status = stdout.channel.recv_exit_status()

            log_parts = []
            if capture:
                if out_text:
                    log_parts.append(f"STDOUT:\n{out_text}")
                if err_text:
                    log_parts.append(f"STDERR:\n{err_text}")
            log_parts.append(f"Exit status: {exit_status}")
            logs = "\n\n".join(log_parts)

            output_vars: dict[str, str] = {}
            if output_var and out_text:
                output_vars[output_var] = out_text

            # Save stdout (and optionally stderr) to a file so it can be
            # attached to a downstream email step via output_path.
            saved_path = ''
            if save_output:
                default_fn = 'ssh_output_{{ current_date }}.log'
                output_filename = render(
                    self.config.get('output_filename') or default_fn,
                    context,
                )
                output_dir = Path(os.environ.get('FLOWFORGE_OUTPUT_DIR', './output'))
                output_path = output_dir / output_filename
                output_path.parent.mkdir(parents=True, exist_ok=True)

                file_content = out_text
                if include_stderr and err_text:
                    separator = '\n\n--- STDERR ---\n'
                    file_content = (file_content + separator + err_text
                                    if file_content else err_text)

                output_path.write_text(file_content, encoding='utf-8')
                saved_path = str(output_path)
                logger.info("SSH output saved: %s", saved_path)

            if exit_status == 0:
                return StepResult(
                    success=True,
                    logs=logs,
                    output_path=saved_path,
                    output_variables=output_vars,
                )
            else:
                return StepResult(
                    success=False,
                    error=f"Command failed with exit status {exit_status}",
                    logs=logs,
                    output_path=saved_path,
                    output_variables=output_vars,
                )

        except Exception as exc:
            logger.exception("SSH command failed")
            return StepResult(success=False, error=f"SSH error: {exc}")
