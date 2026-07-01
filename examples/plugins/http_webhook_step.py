"""Example plugin step — POST a JSON payload to an arbitrary HTTP endpoint.

Not loaded by default. To try it out, copy this file into your
FLOWFORGE_PLUGIN_DIR (default ./plugins) and restart FlowForge — the
new "http_webhook" step type will then be selectable in the Pipeline
Builder. See docs/plugins.md for the full authoring guide.

Config:
    url          Target URL (required)
    method       HTTP method (default: "POST")
    json_body    dict — rendered as Jinja2 strings, then JSON-encoded
    headers      dict — extra request headers (optional)
"""
import json
import logging
import urllib.error
import urllib.request
from typing import Any

from flowforge.steps.base import BaseStep, StepResult

logger = logging.getLogger(__name__)


class HttpWebhookStep(BaseStep):
    step_type = 'http_webhook'

    def run(self, context: dict[str, Any]) -> StepResult:
        from flowforge.engine.context import render

        url = str(self.config.get('url', '')).strip()
        if not url:
            return StepResult(success=False, error='url is required')

        method  = str(self.config.get('method', 'POST')).upper()
        headers = {'Content-Type': 'application/json', **self.config.get('headers', {})}
        raw_body = self.config.get('json_body', {}) or {}
        body = {k: render(str(v), context) for k, v in raw_body.items()}

        req = urllib.request.Request(
            url, data=json.dumps(body).encode(), headers=headers, method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310
                status = resp.status
        except urllib.error.HTTPError as e:
            return StepResult(success=False, error=f'{method} {url} returned HTTP {e.code}: {e.read().decode()[:200]}')
        except Exception as e:
            return StepResult(success=False, error=f'{method} {url} failed: {e}')

        logger.info("http_webhook: %s %s -> %d", method, url, status)
        return StepResult(success=True, logs=f'{method} {url} -> HTTP {status}')
