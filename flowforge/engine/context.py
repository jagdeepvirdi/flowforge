"""
Pipeline variable context: built-in date/run vars + Jinja2 rendering.

Built-in variables available in all config strings:
  {{ current_date }}   — YYYY-MM-DD
  {{ current_month }}  — YYYY-MM
  {{ current_year }}   — YYYY
  {{ yesterday }}      — YYYY-MM-DD
  {{ week_start }}     — YYYY-MM-DD  (Monday of current ISO week)
  {{ week_end }}       — YYYY-MM-DD  (Sunday of current ISO week)
  {{ month_start }}    — YYYY-MM-DD  (first day of current month)
  {{ month_end }}      — YYYY-MM-DD  (last day of current month)
  {{ quarter_start }}  — YYYY-MM-DD  (first day of current quarter)
  {{ quarter_end }}    — YYYY-MM-DD  (last day of current quarter)
  {{ timestamp }}      — DDMMYYYYHHmmSS  (e.g. 18052026142304) — unique per second
  {{ run_id }}         — UUID of the current pipeline run
  {{ pipeline_name }}  — name of the running pipeline
  {{ env.VAR }}        — any environment variable
  {{ steps.name.output_path }}  — output file from a previous step
  {{ steps.name.drive_url }}    — Drive URL from a previous step
"""
import calendar
import os
from datetime import date, datetime, timedelta
from typing import Any
from uuid import uuid4

from jinja2 import Environment, Undefined

_jinja = Environment(undefined=Undefined)


def _built_ins() -> dict[str, Any]:
    now = datetime.now()
    today = now.date()

    week_start = today - timedelta(days=today.weekday())          # Monday
    week_end   = week_start + timedelta(days=6)                   # Sunday

    month_start = today.replace(day=1)
    month_end   = today.replace(day=calendar.monthrange(today.year, today.month)[1])

    q_start_month = (today.month - 1) // 3 * 3 + 1               # 1, 4, 7, or 10
    quarter_start = date(today.year, q_start_month, 1)
    q_end_month   = q_start_month + 2
    quarter_end   = date(today.year, q_end_month, calendar.monthrange(today.year, q_end_month)[1])

    return {
        'current_date':  today.strftime('%Y-%m-%d'),
        'current_month': today.strftime('%Y-%m'),
        'current_year':  str(today.year),
        'yesterday':     (today - timedelta(days=1)).strftime('%Y-%m-%d'),
        'week_start':    week_start.strftime('%Y-%m-%d'),
        'week_end':      week_end.strftime('%Y-%m-%d'),
        'month_start':   month_start.strftime('%Y-%m-%d'),
        'month_end':     month_end.strftime('%Y-%m-%d'),
        'quarter_start': quarter_start.strftime('%Y-%m-%d'),
        'quarter_end':   quarter_end.strftime('%Y-%m-%d'),
        'timestamp':     now.strftime('%d%m%Y%H%M%S'),
        'run_id':        str(uuid4()),
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
        ctx.update(pipeline_vars)          # {{ mykey }}
        ctx['vars'] = pipeline_vars        # {{ vars.mykey }} — explicit namespace
    return ctx


def render(template_str: str, context: dict[str, Any]) -> str:
    """Render a Jinja2 template string against the pipeline context."""
    return _jinja.from_string(template_str).render(**context)
