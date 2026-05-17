"""
Pipeline variable context: built-in date/run vars + Jinja2 rendering.

Built-in variables available in all config strings:
  {{ current_date }}   — YYYY-MM-DD
  {{ current_month }}  — YYYY-MM
  {{ current_year }}   — YYYY
  {{ yesterday }}      — YYYY-MM-DD
  {{ run_id }}         — UUID of the current pipeline run
  {{ pipeline_name }}  — name of the running pipeline
  {{ env.VAR }}        — any environment variable
  {{ steps.name.output_path }}  — output file from a previous step
  {{ steps.name.drive_url }}    — Drive URL from a previous step
"""
import os
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from jinja2 import Environment, Undefined

_jinja = Environment(undefined=Undefined)


def _built_ins() -> dict[str, Any]:
    today = datetime.today()
    return {
        'current_date': today.strftime('%Y-%m-%d'),
        'current_month': today.strftime('%Y-%m'),
        'current_year': str(today.year),
        'yesterday': (today - timedelta(days=1)).strftime('%Y-%m-%d'),
        'run_id': str(uuid4()),
    }


def build(
    pipeline_name: str,
    step_results: dict[str, Any] | None = None,
    pipeline_vars: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Assemble the full variable context for a pipeline run."""
    ctx: dict[str, Any] = _built_ins()
    ctx['pipeline_name'] = pipeline_name
    ctx['env'] = os.environ
    ctx['steps'] = step_results or {}
    if pipeline_vars:
        ctx.update(pipeline_vars)
    return ctx


def render(template_str: str, context: dict[str, Any]) -> str:
    """Render a Jinja2 template string against the pipeline context."""
    return _jinja.from_string(template_str).render(**context)
