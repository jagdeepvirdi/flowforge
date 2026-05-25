"""
Pipeline variable context: built-in date/run vars + Jinja2 rendering.

Built-in variables available in all config strings:

  Date (YYYY-MM-DD):
    {{ current_date }}      today
    {{ yesterday }}         yesterday
    {{ week_start }}        Monday of current ISO week
    {{ week_end }}          Sunday of current ISO week
    {{ month_start }}       first day of current month
    {{ month_end }}         last day of current month
    {{ prev_month_start }}  first day of previous month
    {{ prev_month_end }}    last day of previous month
    {{ quarter_start }}     first day of current quarter
    {{ quarter_end }}       last day of current quarter

  Timestamp boundaries (YYYYMMDDHHmmSS) — for date-range WHERE clauses:
    {{ day_start_ts }}          today at 00:00:00   e.g. 20260522000000
    {{ day_end_ts }}            today at 23:59:59   e.g. 20260522235959
    {{ yesterday_start_ts }}    yesterday at 00:00:00
    {{ yesterday_end_ts }}      yesterday at 23:59:59
    {{ month_start_ts }}        first of month at 00:00:00
    {{ month_end_ts }}          last of month  at 23:59:59
    {{ prev_month_start_ts }}   first of previous month at 00:00:00
    {{ prev_month_end_ts }}     last  of previous month at 23:59:59

  Other:
    {{ current_month }}     YYYY-MM
    {{ current_year }}      YYYY
    {{ mon_year }}          MON-YYYY  e.g. AUG-2026  (for human-readable filenames)
    {{ timestamp }}         DDMMYYYYHHmmSS (unique per second, for filenames)
    {{ now_ts }}            YYYYMMDDHHmmSS e.g. 20260824223155 (sortable filename timestamp)
    {{ run_id }}            UUID of the current pipeline run
    {{ pipeline_name }}     name of the running pipeline
    {{ last_success_at }}   YYYYMMDDHHmmSS of the last successful run (set by runner)
    {{ last_success_date }} YYYY-MM-DD of the last successful run  (set by runner)
    {{ env.VAR }}           any environment variable (see FLOWFORGE_TEMPLATE_ENV_VARS)
    {{ steps.name.* }}      outputs from a previous step
"""
import calendar
import logging
import os
from datetime import date, datetime, timedelta
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_BUILT_IN_VAR_KEYS = frozenset({
    'current_date', 'current_month', 'current_year',
    'yesterday', 'week_start', 'week_end',
    'month_start', 'month_end', 'prev_month_start', 'prev_month_end',
    'quarter_start', 'quarter_end',
    'day_start_ts', 'day_end_ts',
    'yesterday_start_ts', 'yesterday_end_ts',
    'month_start_ts', 'month_end_ts',
    'prev_month_start_ts', 'prev_month_end_ts',
    'timestamp', 'now_ts', 'mon_year', 'run_id', 'pipeline_name',
    'last_success_at', 'last_success_date',
    'env', 'steps', 'vars',
})

from jinja2 import Undefined
from jinja2.sandbox import SandboxedEnvironment

_jinja = SandboxedEnvironment(undefined=Undefined)

# Fallback blocklist used when FLOWFORGE_TEMPLATE_ENV_VARS is not set.
# Prevents known credential vars from leaking into templates in the default
# (backward-compatible) mode.  Prefer setting FLOWFORGE_TEMPLATE_ENV_VARS
# to an explicit comma-separated allowlist instead.
_ENV_BLOCKLIST = frozenset({
    'FLOWFORGE_SECRET_KEY',
    'FLOWFORGE_PASSWORD',
    'FLOWFORGE_JWT_SECRET',
    'GMAIL_CLIENT_SECRET',
    'GMAIL_REFRESH_TOKEN',
    'MICROSOFT_CLIENT_SECRET',
    'ANTHROPIC_API_KEY',
})


class _SafeEnv:
    """Read-only view of os.environ for use in pipeline templates.

    Two modes, selected at instantiation time:

    Allowlist mode (recommended):
        Set FLOWFORGE_TEMPLATE_ENV_VARS=VAR1,VAR2 in the environment.
        Only the listed variable names are accessible; all others return ''.
        Example: FLOWFORGE_TEMPLATE_ENV_VARS=DB_HOST,REPORT_DIR,APP_ENV

    Blocklist mode (default, backward-compatible):
        When FLOWFORGE_TEMPLATE_ENV_VARS is not set, any env var is accessible
        EXCEPT those in _ENV_BLOCKLIST (known credential names).
        This mode is provided for existing deployments; migrating to allowlist
        mode is strongly recommended.
    """

    def __init__(self) -> None:
        raw = os.environ.get('FLOWFORGE_TEMPLATE_ENV_VARS', '').strip()
        self._allowlist: frozenset[str] | None = (
            frozenset(v.strip() for v in raw.split(',') if v.strip())
            if raw else None
        )

    def _allowed(self, key: str) -> bool:
        if self._allowlist is not None:
            return key in self._allowlist
        return key not in _ENV_BLOCKLIST

    def __getitem__(self, key: str) -> str:
        return os.environ.get(key, '') if self._allowed(key) else ''

    def get(self, key: str, default: str = '') -> str:
        return os.environ.get(key, default) if self._allowed(key) else default


def _built_ins() -> dict[str, Any]:
    now = datetime.now()
    today = now.date()

    week_start = today - timedelta(days=today.weekday())          # Monday
    week_end   = week_start + timedelta(days=6)                   # Sunday

    yesterday   = today - timedelta(days=1)

    month_start = today.replace(day=1)
    month_end   = today.replace(day=calendar.monthrange(today.year, today.month)[1])

    # Previous month
    prev_month_end_day = month_start - timedelta(days=1)
    prev_month_start   = prev_month_end_day.replace(day=1)

    q_start_month = (today.month - 1) // 3 * 3 + 1               # 1, 4, 7, or 10
    quarter_start = date(today.year, q_start_month, 1)
    q_end_month   = q_start_month + 2
    quarter_end   = date(today.year, q_end_month, calendar.monthrange(today.year, q_end_month)[1])

    _ts = lambda d, h, m, s: f"{d.strftime('%Y%m%d')}{h:02d}{m:02d}{s:02d}"

    return {
        # Date strings (YYYY-MM-DD)
        'current_date':     today.strftime('%Y-%m-%d'),
        'current_month':    today.strftime('%Y-%m'),
        'current_year':     str(today.year),
        'yesterday':        yesterday.strftime('%Y-%m-%d'),
        'week_start':       week_start.strftime('%Y-%m-%d'),
        'week_end':         week_end.strftime('%Y-%m-%d'),
        'month_start':      month_start.strftime('%Y-%m-%d'),
        'month_end':        month_end.strftime('%Y-%m-%d'),
        'prev_month_start': prev_month_start.strftime('%Y-%m-%d'),
        'prev_month_end':   prev_month_end_day.strftime('%Y-%m-%d'),
        'quarter_start':    quarter_start.strftime('%Y-%m-%d'),
        'quarter_end':      quarter_end.strftime('%Y-%m-%d'),

        # Timestamp boundaries (YYYYMMDDHHmmSS) for date-range WHERE clauses
        'day_start_ts':         _ts(today, 0, 0, 0),
        'day_end_ts':           _ts(today, 23, 59, 59),
        'yesterday_start_ts':   _ts(yesterday, 0, 0, 0),
        'yesterday_end_ts':     _ts(yesterday, 23, 59, 59),
        'month_start_ts':       _ts(month_start, 0, 0, 0),
        'month_end_ts':         _ts(month_end, 23, 59, 59),
        'prev_month_start_ts':  _ts(prev_month_start, 0, 0, 0),
        'prev_month_end_ts':    _ts(prev_month_end_day, 23, 59, 59),

        # Run metadata
        'timestamp':    now.strftime('%d%m%Y%H%M%S'),
        'now_ts':       now.strftime('%Y%m%d%H%M%S'),
        'mon_year':     now.strftime('%b').upper() + '-' + now.strftime('%Y'),
        'run_id':       str(uuid4()),
    }


def build(
    pipeline_name: str,
    step_results: dict[str, Any] | None = None,
    pipeline_vars: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Assemble the full variable context for a pipeline run."""
    ctx: dict[str, Any] = _built_ins()
    ctx['pipeline_name'] = pipeline_name
    ctx['env'] = _SafeEnv()
    ctx['steps'] = step_results or {}
    if pipeline_vars:
        collisions = _BUILT_IN_VAR_KEYS & pipeline_vars.keys()
        if collisions:
            logger.warning(
                'Pipeline variable(s) overwrite built-in context keys: %s',
                ', '.join(sorted(collisions)),
            )
        ctx.update(pipeline_vars)          # {{ mykey }}
        ctx['vars'] = pipeline_vars        # {{ vars.mykey }} — explicit namespace
    return ctx


def render(template_str: str, context: dict[str, Any]) -> str:
    """Render a Jinja2 template string against the pipeline context."""
    return _jinja.from_string(template_str).render(**context)
