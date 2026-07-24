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
import html as _html
import logging
import os
from datetime import date, datetime, timedelta
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

# SEC-02: blocklist mode (see _SafeEnv) can never be exhaustive against new
# credential-shaped env vars, so its use is deprecated in favor of an explicit
# allowlist. Logged once per process, not once per _SafeEnv() construction —
# build() constructs a new _SafeEnv on every pipeline step, which would
# otherwise spam this warning on every run of every pipeline.
_blocklist_mode_warned = False

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
    'FLOWFORGE_DB_URL',
    'FLOWFORGE_REDIS_URL',
    'GMAIL_CLIENT_SECRET',
    'GMAIL_REFRESH_TOKEN',
    'MICROSOFT_CLIENT_SECRET',
    'GOOGLE_SSO_CLIENT_SECRET',
    'MICROSOFT_SSO_CLIENT_SECRET',
    'ANTHROPIC_API_KEY',
    'GEMINI_API_KEY',
    'AWS_ACCESS_KEY_ID',
    'AWS_SECRET_ACCESS_KEY',
    'AZURE_STORAGE_ACCOUNT_KEY',
    'AZURE_STORAGE_CONNECTION_STRING',
    'SAML_IDP_X509_CERT',
    'DB_PASSWORD',
})

# Defense-in-depth: block anything whose *name* looks like a credential, even
# if it's missing from the explicit list above. New integrations keep adding
# new credential env vars (AWS/Azure/SSO keys were all missing from this list
# until this comment was added) — a name-pattern catches the next one too.
_SENSITIVE_NAME_KEYWORDS = ('SECRET', 'PASSWORD', 'PASSWD', 'TOKEN', 'KEY', 'CERT', 'CONN', 'DSN', '_URL')


def _looks_like_credential_name(name: str) -> bool:
    return any(kw in name for kw in _SENSITIVE_NAME_KEYWORDS)


class _SafeEnv:
    """Read-only view of os.environ for use in pipeline templates.

    Two modes, selected at instantiation time:

    Allowlist mode (recommended):
        Set FLOWFORGE_TEMPLATE_ENV_VARS=VAR1,VAR2 in the environment.
        Only the listed variable names are accessible; all others return ''.
        Example: FLOWFORGE_TEMPLATE_ENV_VARS=DB_HOST,REPORT_DIR,APP_ENV

    Blocklist mode (deprecated, backward-compatible):
        When FLOWFORGE_TEMPLATE_ENV_VARS is not set, any env var is accessible
        EXCEPT those in _ENV_BLOCKLIST (known credential names) or whose name
        looks like a credential (see _looks_like_credential_name). A blocklist
        can never be exhaustive against the next credential-shaped env var a
        future integration adds, so this mode logs a one-time deprecation
        warning and remains only for existing deployments — migrate to
        allowlist mode.
    """

    def __init__(self) -> None:
        raw = os.environ.get('FLOWFORGE_TEMPLATE_ENV_VARS', '').strip()
        if raw:
            self._allowlist: frozenset[str] | None = frozenset(
                v.strip() for v in raw.split(',') if v.strip()
            )
            self._validate_allowlist(self._allowlist)
        else:
            self._allowlist = None
            self._warn_blocklist_mode_deprecated()

    @staticmethod
    def _warn_blocklist_mode_deprecated() -> None:
        global _blocklist_mode_warned
        if _blocklist_mode_warned:
            return
        _blocklist_mode_warned = True
        logger.warning(
            'DEPRECATED: FLOWFORGE_TEMPLATE_ENV_VARS is not set, so pipeline templates can '
            'read any environment variable except a hardcoded credential blocklist. This '
            'blocklist can never be exhaustive against new credential-shaped env vars added '
            'by future integrations. Set FLOWFORGE_TEMPLATE_ENV_VARS to an explicit '
            'comma-separated allowlist (e.g. FLOWFORGE_TEMPLATE_ENV_VARS=DB_HOST,REPORT_DIR) '
            'instead — blocklist mode may be removed in a future release.'
        )

    @staticmethod
    def _validate_allowlist(allowlist: frozenset[str]) -> None:
        """Strict validation: flag (but do not block) credential-shaped names an
        operator explicitly allowlisted. Allowlist mode is opt-in and explicit —
        an explicitly-listed var is still exposed — this only surfaces likely
        misconfiguration (e.g. a name copy-pasted from _ENV_BLOCKLIST by mistake).
        """
        suspicious = sorted(name for name in allowlist if _looks_like_credential_name(name))
        if suspicious:
            logger.warning(
                'FLOWFORGE_TEMPLATE_ENV_VARS explicitly allowlists credential-shaped '
                'variable name(s), which will be exposed to pipeline templates verbatim: %s. '
                'Confirm this is intentional.',
                ', '.join(suspicious),
            )

    def _allowed(self, key: str) -> bool:
        if self._allowlist is not None:
            return key in self._allowlist
        return key not in _ENV_BLOCKLIST and not _looks_like_credential_name(key)

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

    def _ts(d, h, m, s):
        return f"{d.strftime('%Y%m%d')}{h:02d}{m:02d}{s:02d}"

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


class SecretLeakError(ValueError):
    """Raised when a template references a secret pipeline variable in a sink where
    the rendered value could be persisted, displayed, or transmitted outside the
    pipeline's own trust boundary (SQL text, email bodies, notifications, AI prompts)."""


def _referenced_secrets(template_str: str, context: dict[str, Any]) -> set[str]:
    secret_keys: set[str] = context.get('_secret_var_keys') or set()
    if not secret_keys or not template_str:
        return set()
    try:
        from jinja2 import meta as _meta
        ast = _jinja.parse(template_str)
        referenced = _meta.find_undeclared_variables(ast)
    except Exception:  # nosec B110 — don't block execution on template-parse errors
        return set()
    return referenced & secret_keys


def render(template_str: str, context: dict[str, Any]) -> str:
    """Render a Jinja2 template string against the pipeline context."""
    return _jinja.from_string(template_str).render(**context)


def render_guarded(template_str: str, context: dict[str, Any], *, sink: str = 'this field') -> str:
    """Render a template, hard-blocking if a secret pipeline variable is referenced.

    Use for any output that leaves the pipeline's own trust boundary — SQL text
    (which may be captured to an output table, capture_rows, or run-history logs),
    email bodies, chat notifications, or AI prompts. Secret pipeline variables must
    not flow into these sinks; pass secrets via db_procedure 'params' instead —
    those flow as bind variables and are never embedded in rendered text.
    """
    secrets_used = _referenced_secrets(template_str, context)
    if secrets_used:
        raise SecretLeakError(
            f"Refusing to render {sink}: references secret pipeline variable(s) "
            f"{', '.join(sorted(secrets_used))}. Secret variables cannot be used here — "
            "the rendered result may be persisted, displayed, or transmitted outside the "
            "pipeline. Pass secrets via db_procedure 'params' (bind variables) instead."
        )
    return _jinja.from_string(template_str).render(**context)


def _paragraphize(html_text: str) -> str:
    """Wrap already-safe HTML text into <p>/<br> paragraphs (no escaping)."""
    paragraphs = html_text.replace('\r\n', '\n').split('\n\n')
    html_paragraphs = [
        f'<p>{para.replace(chr(10), "<br>" + chr(10))}</p>'
        for para in paragraphs if para.strip()
    ]
    return '\n'.join(html_paragraphs)


def text_to_html(text: str) -> str:
    """Convert a plain-text (Jinja2-rendered) email body into an HTML fragment.

    Used for the "simple document" body format, where the user writes plain
    text + Jinja2 and never touches HTML tags. Blank lines start a new <p>;
    single newlines within a paragraph become <br>. All text is HTML-escaped
    so the result is always a safe fragment, even if the rendered text
    happens to contain characters like < or &.
    """
    return _paragraphize(_html.escape(text))


_HTML_SAFE_STEP_KEYS = ('table_html', 'kv_html')


def _replace_safe_html_with_placeholders(context: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    """Swap known-safe HTML fragments (a step's table_html/kv_html) for unique
    placeholder tokens before rendering, so render_simple_document() can escape
    the rendered body as a whole and then splice the real markup back in —
    without escaping fragments that are already safe HTML.
    """
    steps = context.get('steps')
    if not steps:
        return context, {}

    placeholders: dict[str, str] = {}
    safe_steps = {}
    for step_name, data in steps.items():
        if isinstance(data, dict) and any(data.get(k) for k in _HTML_SAFE_STEP_KEYS):
            new_data = dict(data)
            for key in _HTML_SAFE_STEP_KEYS:
                value = data.get(key)
                if value:
                    token = f'￹HTMLSAFE{uuid4().hex}￻'
                    placeholders[token] = value
                    new_data[key] = token
            safe_steps[step_name] = new_data
        else:
            safe_steps[step_name] = data
    return {**context, 'steps': safe_steps}, placeholders


def render_simple_document(template_str: str, context: dict[str, Any], *, sink: str = 'this field') -> str:
    """Render a "Simple document" (plain-text + Jinja2) template into an HTML fragment.

    Like render_guarded(), but the whole rendered body is HTML-escaped —
    except for known-safe HTML fragments produced by earlier steps (a step's
    `table_html` / `kv_html` output), which are spliced back in unescaped so
    query-result tables render as tables instead of showing up as literal
    HTML source. Blank lines start a new <p>; single newlines become <br>.
    """
    secrets_used = _referenced_secrets(template_str, context)
    if secrets_used:
        raise SecretLeakError(
            f"Refusing to render {sink}: references secret pipeline variable(s) "
            f"{', '.join(sorted(secrets_used))}. Secret variables cannot be used here — "
            "the rendered result may be persisted, displayed, or transmitted outside the "
            "pipeline. Pass secrets via db_procedure 'params' (bind variables) instead."
        )
    safe_context, placeholders = _replace_safe_html_with_placeholders(context)
    rendered = _jinja.from_string(template_str).render(**safe_context)
    escaped = _html.escape(rendered)
    for token, html_fragment in placeholders.items():
        escaped = escaped.replace(token, html_fragment)
    return _paragraphize(escaped)


def render_sql(template_str: str, context: dict[str, Any]) -> str:
    """Render a SQL template string, hard-blocking if a secret pipeline variable is referenced.

    See render_guarded() — SQL text is a leak vector because query results can be
    captured to an output table, capture_rows, run-history logs, or an email body.
    """
    return render_guarded(template_str, context, sink='SQL query')
