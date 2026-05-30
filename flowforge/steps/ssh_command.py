"""SSH command step — execute remote commands or scripts via paramiko."""
import logging
from typing import Any

from flowforge.steps.base import BaseStep, StepResult

logger = logging.getLogger(__name__)


class SshCommandStep(BaseStep):
    """Execute remote commands or scripts via SSH.

    Config fields:
        ssh_connection_id   ID of the SSHConnection row  (required)
        command             Command to execute — supports {{ variables }}  (required)
        timeout             Command execution timeout in seconds  (default: 60)
        capture_output      Whether to capture stdout/stderr in logs (default: true)
        output_var          Name of the context variable to store stdout in (optional)
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

        timeout = int(self.config.get('timeout', 60))
        capture = bool(self.config.get('capture_output', True))
        output_var = self.config.get('output_var')

        try:
            conn = get_ssh_connection(conn_id)
            with conn:
                logger.info("SSH: executing command on %s: %s", conn.host, command)
                
                # exec_command returns (stdin, stdout, stderr)
                stdin, stdout, stderr = conn.client.exec_command(command, timeout=timeout)
                
                # stdin must be closed if not used
                stdin.close()
                
                out_text = stdout.read().decode('utf-8', errors='replace').strip()
                err_text = stderr.read().decode('utf-8', errors='replace').strip()
                exit_status = stdout.channel.recv_exit_status()
                
                log_parts = []
                if capture:
                    if out_text:
                        log_parts.append(f"STDOUT:\n{out_text}")
                    if err_text:
                        log_parts.append(f"STDERR:\n{err_text}")
                
                log_parts.append(f"Exit status: {exit_status}")
                logs = "\n\n".join(log_parts)

                output_vars = {}
                if output_var and out_text:
                    output_vars[output_var] = out_text

                if exit_status == 0:
                    return StepResult(success=True, logs=logs, output_variables=output_vars)
                else:
                    return StepResult(
                        success=False,
                        error=f"Command failed with exit status {exit_status}",
                        logs=logs,
                        output_variables=output_vars,
                    )

        except Exception as exc:
            logger.exception("SSH command failed")
            return StepResult(success=False, error=f"SSH error: {exc}")
