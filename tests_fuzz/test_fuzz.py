"""Property-based / fuzz tests using Hypothesis.

These tests verify that FlowForge's core parsing and rendering functions
handle arbitrary inputs without crashing, panicking, or leaking secrets.

Run deterministically in CI with:  pytest tests_fuzz/ --hypothesis-seed=0
Run with full exploration locally:  pytest tests_fuzz/
"""
import os
import re
from unittest.mock import patch

from hypothesis import given, settings, assume
from hypothesis import strategies as st

# ── helpers ──────────────────────────────────────────────────────────────────

# Identifier-safe text for pipeline variable names.
# Restricted to [a-z][a-z0-9_]* to avoid Jinja2 keywords (True/False/None)
# and names starting with digits which Jinja2 treats as literals.
_IDENT = st.from_regex(r'[a-z][a-z0-9_]{0,39}', fullmatch=True)

# Env var values that are safe to set (no null bytes — invalid on all platforms)
_ENV_VALUE = st.text(max_size=200, alphabet=st.characters(blacklist_characters='\x00'))

# Jinja2 reserved names that resolve as literals, not pipeline vars
_JINJA2_KEYWORDS = frozenset({
    'true', 'false', 'none', 'True', 'False', 'None',
    'not', 'and', 'or', 'in', 'is', 'loop', 'super',
})

_BLOCKLIST = frozenset({
    'FLOWFORGE_SECRET_KEY',
    'FLOWFORGE_PASSWORD',
    'FLOWFORGE_JWT_SECRET',
    'GMAIL_CLIENT_SECRET',
    'GMAIL_REFRESH_TOKEN',
    'MICROSOFT_CLIENT_SECRET',
    'ANTHROPIC_API_KEY',
})

_TS_RE = re.compile(r'^\d{14}$')
_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


# ── context.build() invariants ───────────────────────────────────────────────

@given(name=st.text(max_size=200))
@settings(max_examples=200)
def test_build_always_contains_required_keys(name):
    """build() must always produce all built-in date/run keys regardless of pipeline name."""
    from flowforge.engine.context import build
    ctx = build(name)
    required = {
        'current_date', 'current_month', 'current_year',
        'yesterday', 'run_id', 'pipeline_name',
        'day_start_ts', 'day_end_ts',
    }
    for key in required:
        assert key in ctx, f"Missing key: {key}"


@given(name=st.text(max_size=200))
@settings(max_examples=200)
def test_build_pipeline_name_round_trips(name):
    """pipeline_name in context must be the exact string passed to build()."""
    from flowforge.engine.context import build
    ctx = build(name)
    assert ctx['pipeline_name'] == name


@given(name=st.text(max_size=200))
@settings(max_examples=100)
def test_build_date_vars_have_correct_format(name):
    """Date vars must always be YYYY-MM-DD regardless of pipeline name."""
    from flowforge.engine.context import build
    ctx = build(name)
    for key in ('current_date', 'yesterday', 'month_start', 'month_end'):
        assert _DATE_RE.match(ctx[key]), f"{key}={ctx[key]!r} doesn't match YYYY-MM-DD"


@given(name=st.text(max_size=200))
@settings(max_examples=100)
def test_build_timestamp_vars_are_14_digits(name):
    """All *_ts vars must be 14-digit YYYYMMDDHHmmSS strings."""
    from flowforge.engine.context import build
    ctx = build(name)
    for key in ('day_start_ts', 'day_end_ts', 'yesterday_start_ts', 'month_start_ts'):
        assert _TS_RE.match(ctx[key]), f"{key}={ctx[key]!r} is not 14 digits"


# ── context.render() robustness ───────────────────────────────────────────────

@given(template=st.text(max_size=500))
@settings(max_examples=500)
def test_render_never_panics_on_arbitrary_text(template):
    """render() must never raise an unexpected exception on arbitrary template strings.

    Jinja2 TemplateSyntaxError / TemplateError are acceptable outcomes; anything
    else (AttributeError, RecursionError, etc.) is a bug.
    """
    from jinja2 import TemplateError
    from flowforge.engine.context import build, render
    ctx = build('fuzz')
    try:
        result = render(template, ctx)
        assert isinstance(result, str)
    except TemplateError:
        pass  # expected: malformed template syntax


@given(
    key=_IDENT,
    value=st.text(max_size=200),
)
@settings(max_examples=300)
def test_render_pipeline_var_round_trip(key, value):
    """{{ key }} must render to exactly the value stored in pipeline_vars."""
    assume(key not in _JINJA2_KEYWORDS)
    assume(key not in {
        'env', 'steps', 'vars', 'current_date', 'run_id', 'pipeline_name',
        'current_month', 'current_year', 'yesterday',
    })
    from jinja2 import TemplateError
    from flowforge.engine.context import build, render
    ctx = build('fuzz', pipeline_vars={key: value})
    try:
        result = render(f'{{{{ {key} }}}}', ctx)
        assert result == value
    except TemplateError:
        pass


@given(
    prefix=st.text(min_size=0, max_size=30, alphabet='abcdefghijklmnopqrstuvwxyz0123456789_-'),
    suffix=st.text(min_size=1, max_size=10, alphabet='abcdefghijklmnopqrstuvwxyz'),
)
@settings(max_examples=200)
def test_filename_templates_always_resolve(prefix, suffix):
    """Output filename templates using date vars must not contain unrendered {{ }}."""
    from flowforge.engine.context import build, render
    ctx = build('fuzz')
    template = f'{prefix}_{{{{ current_month }}}}.{suffix}'
    result = render(template, ctx)
    assert '{{' not in result
    assert '}}' not in result
    assert result.endswith(f'.{suffix}')


# ── _SafeEnv blocklist invariants ────────────────────────────────────────────

@given(
    var_name=st.sampled_from(sorted(_BLOCKLIST)),
    var_value=_ENV_VALUE,
)
@settings(max_examples=100)
def test_blocklisted_env_vars_always_render_empty(var_name, var_value):
    """Blocklisted credential env vars must never appear in rendered output."""
    from flowforge.engine.context import build, render
    with patch.dict(os.environ, {var_name: var_value}, clear=False):
        ctx = build('fuzz')
        result = render(f'{{{{ env.{var_name} }}}}', ctx)
    assert result == '', f"{var_name} leaked: got {result!r}"
    if var_value:
        assert var_value not in result


@given(
    var_name=st.sampled_from(sorted(_BLOCKLIST)),
    var_value=st.text(min_size=4, max_size=200, alphabet=st.characters(blacklist_characters='\x00')),
)
@settings(max_examples=100)
def test_blocklisted_vars_not_in_any_render(var_name, var_value):
    """Credential values must not appear when rendered via the direct env.VAR pattern."""
    assume(var_value.strip())
    from jinja2 import TemplateError
    from flowforge.engine.context import build, render
    with patch.dict(os.environ, {var_name: var_value}, clear=False):
        ctx = build('fuzz')
        # Only test the documented access pattern {{ env.VAR_NAME }}
        # ({{ env }} exposes the _SafeEnv object repr — not a real usage)
        for tmpl in [
            f'{{{{ env.{var_name} }}}}',
            f'prefix_{{{{ env.{var_name} }}}}_suffix',
        ]:
            try:
                result = render(tmpl, ctx)
                assert var_value not in result, (
                    f"Secret leaked via template {tmpl!r}: {result!r}"
                )
            except TemplateError:
                pass


# ── context.render_sql() robustness ──────────────────────────────────────────

@given(sql=st.text(max_size=500))
@settings(max_examples=300)
def test_render_sql_never_panics(sql):
    """render_sql() must never raise unexpected exceptions on arbitrary SQL strings."""
    from jinja2 import TemplateError
    from flowforge.engine.context import build, render_sql
    ctx = build('fuzz')
    ctx['_secret_var_keys'] = set()
    try:
        result = render_sql(sql, ctx)
        assert isinstance(result, str)
    except TemplateError:
        pass


@given(
    sql=st.text(max_size=500),
    secret_keys=st.frozensets(st.text(min_size=1, max_size=20, alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ_'), max_size=5),
)
@settings(max_examples=200)
def test_render_sql_with_secret_keys_never_panics(sql, secret_keys):
    """render_sql() must handle arbitrary secret_key sets without crashing."""
    from jinja2 import TemplateError
    from flowforge.engine.context import build, render_sql
    ctx = build('fuzz')
    ctx['_secret_var_keys'] = set(secret_keys)
    try:
        render_sql(sql, ctx)
    except TemplateError:
        pass


# ── Pipeline variable injection safety ───────────────────────────────────────

@given(
    vars_dict=st.dictionaries(
        keys=_IDENT,
        values=st.text(max_size=100),
        max_size=10,
    )
)
@settings(max_examples=200)
def test_pipeline_vars_never_corrupt_context_type(vars_dict):
    """Pipeline vars must not make the context non-dict or remove required keys."""
    from flowforge.engine.context import build
    ctx = build('fuzz', pipeline_vars=vars_dict)
    assert isinstance(ctx, dict)
    assert 'run_id' in ctx
    assert 'env' in ctx
    assert 'steps' in ctx
