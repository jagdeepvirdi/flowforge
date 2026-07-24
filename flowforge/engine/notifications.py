"""External run-completion notifications fired by the runner.

Both of these are best-effort side channels — a delivery failure is logged
and swallowed, never raised, so a notification outage can't fail a pipeline
run.
"""
import json
import logging
import os
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)


def _fire_failure_webhook(url: str, payload: dict) -> None:
    """POST JSON payload to the failure webhook URL; errors are logged, never raised."""
    if not url:
        return
    try:
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            url,
            data=body,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=10):  # nosec B310
            pass
        logger.info("Failure webhook delivered to %s", url)
    except Exception as exc:
        logger.warning("Failure webhook POST to %s failed: %s", url, exc)


def _notify_devbrain(
    pipeline_name: str, run_id: str, success: bool,
    error_step: str = '', error_message: str = '',
) -> None:
    """POST a run-completion notification to DevBrain's /api/notify hook.

    Gated by FLOWFORGE_DEVBRAIN_NOTIFY_URL (e.g. http://localhost:3001/api/notify) — unset by
    default, so this is a no-op unless the operator has DevBrain running and wants pipeline
    completions surfaced there. Fires on every run (success and failure), unlike
    on_failure_webhook_url above which is failure-only and per-pipeline-configured.
    """
    url = os.environ.get('FLOWFORGE_DEVBRAIN_NOTIFY_URL', '')
    if not url:
        return
    if success:
        title = f'Pipeline succeeded: {pipeline_name}'
        body = f'Run {run_id} completed successfully.'
    else:
        title = f'Pipeline failed: {pipeline_name}'
        body = f"Run {run_id} failed at step '{error_step}': {error_message}"
    payload = {
        'project': 'flowforge',
        'title':   title,
        'body':    body,
        'level':   'success' if success else 'error',
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=10):  # nosec B310
            pass
        logger.info("DevBrain notification delivered for pipeline %s", pipeline_name)
    except Exception as exc:
        logger.warning("DevBrain notification POST to %s failed: %s", url, exc)
