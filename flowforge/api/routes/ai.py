"""AI utility endpoints — Ollama-only, zero external cost."""
import json
import logging
import os
import urllib.error
import urllib.request

from flask import Blueprint, jsonify, request

from flowforge.api.auth import require_auth

logger = logging.getLogger(__name__)
bp = Blueprint('ai', __name__)

_VALID_CHART_TYPES = {'bar', 'line', 'area', 'pie', 'scatter'}
_VALID_QUERY_TASKS = {'explain', 'optimize', 'diagnose'}


def _ai_enabled() -> bool:
    val = os.environ.get('FLOWFORGE_AI_ENABLED', 'true').lower().strip()
    return val not in ('false', '0', 'no', 'off')


@bp.before_request
def check_ai_enabled():
    if not _ai_enabled():
        return jsonify({'error': 'AI features are disabled. Set FLOWFORGE_AI_ENABLED=true in your .env to enable.'}), 503


def _ollama_url() -> str:
    return os.environ.get('OLLAMA_URL', 'http://localhost:11434').rstrip('/')


def _chart_model() -> str:
    return os.environ.get('OLLAMA_CHART_MODEL', 'llama3.2:3b')


def _query_model() -> str:
    return os.environ.get('OLLAMA_QUERY_MODEL', 'llama3.2:3b')


def _ollama_generate(prompt: str, model: str, *, json_mode: bool = True, timeout: int = 30) -> str:
    """Call Ollama /api/generate. Set json_mode=False for free-text responses."""
    body: dict = {
        'model': model,
        'prompt': prompt,
        'stream': False,
        'options': {'temperature': 0.1},
    }
    if json_mode:
        body['format'] = 'json'
    payload = json.dumps(body).encode()
    req = urllib.request.Request(
        f'{_ollama_url()}/api/generate',
        data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        result = json.loads(resp.read())
    return result.get('response', '')


@bp.post('/ai/data-profile')
@require_auth
def data_profile():
    """Summarise a sample dataset: value ranges, nulls, outliers, key suspicion."""
    data = request.get_json() or {}
    columns: list[str] = data.get('columns', [])
    rows: list[list]   = data.get('rows', [])

    if not columns:
        return jsonify({'error': 'columns required'}), 400

    sample   = rows[:20]
    col_str  = ', '.join(columns)
    row_text = '\n'.join(', '.join(str(c) for c in row) for row in sample)

    prompt = (
        'You are a data analyst. Given these column names and sample rows, write a concise data profile.\n\n'
        f'Columns: {col_str}\n'
        f'Sample data ({len(sample)} rows):\n'
        f'{row_text}\n\n'
        'Write a 3-5 sentence plain-English narrative that covers:\n'
        '- The apparent purpose and structure of this dataset\n'
        '- Value ranges and notable distributions for numeric columns\n'
        '- Any null or empty values observed\n'
        '- Any outliers or suspicious values\n'
        '- Whether any column looks like a unique key (flag if duplicates exist)\n\n'
        'Reference actual values from the data. Be concise and practical.'
    )

    try:
        result = _ollama_generate(prompt, _chart_model(), json_mode=False, timeout=60)
    except urllib.error.URLError:
        url = _ollama_url()
        return jsonify({'error': f'Ollama is not reachable at {url}. Is it running?'}), 503
    except Exception as exc:
        logger.exception('ai/data-profile error: %s', exc)
        return jsonify({'error': str(exc)}), 500

    return jsonify({'result': result.strip()})


@bp.post('/ai/chart-config')
@require_auth
def chart_config():
    """Ask Ollama to suggest the best chart type and axes for a column/row sample."""
    data = request.get_json() or {}
    columns: list[str] = data.get('columns', [])
    rows: list[list] = data.get('rows', [])
    hint: str = str(data.get('hint', '')).strip()

    if not columns:
        return jsonify({'error': 'columns required'}), 400

    sample = rows[:50]
    col_str = ', '.join(columns)
    row_preview = '\n'.join(
        ', '.join(str(c) for c in row) for row in sample[:10]
    )
    hint_line = f'\nUser hint: {hint}' if hint else ''

    prompt = (
        f'You are a data visualization assistant. Given these column names and sample rows, '
        f'choose the best chart.\n\n'
        f'Columns: {col_str}\n'
        f'Sample data ({min(10, len(sample))} rows shown):\n'
        f'{row_preview}{hint_line}\n\n'
        f'Rules:\n'
        f'- bar   — categorical comparisons\n'
        f'- line  — time series or ordered numeric data\n'
        f'- area  — like line but emphasises volume\n'
        f'- pie   — part-of-whole (only when ≤8 distinct categories in x)\n'
        f'- scatter — correlation between two numeric columns\n\n'
        f'Respond with ONLY valid JSON, no extra text:\n'
        f'{{"type": "bar", "x": "column_name", "y": "column_name", "title": "Descriptive chart title"}}'
    )

    try:
        raw = _ollama_generate(prompt, _chart_model(), json_mode=True)
        cfg: dict = json.loads(raw)
    except urllib.error.URLError:
        url = _ollama_url()
        return jsonify({'error': f'Ollama is not reachable at {url}. Is it running?'}), 503
    except json.JSONDecodeError as exc:
        logger.warning('ai/chart-config: bad JSON from Ollama: %s', exc)
        cfg = {}

    # Sanitise — never trust LLM output for field values
    if cfg.get('type') not in _VALID_CHART_TYPES:
        cfg['type'] = 'bar'
    if cfg.get('x') not in columns:
        cfg['x'] = columns[0]
    if cfg.get('y') not in columns:
        cfg['y'] = columns[-1] if len(columns) > 1 else columns[0]
    if not isinstance(cfg.get('title'), str):
        cfg['title'] = ''
    cfg['available_columns'] = columns

    return jsonify(cfg)


@bp.post('/ai/query')
@require_auth
def ai_query():
    """General-purpose AI text endpoint for SQL tasks (explain, optimize, diagnose)."""
    data = request.get_json() or {}
    task: str = str(data.get('task', '')).strip()

    if task not in _VALID_QUERY_TASKS:
        return jsonify({'error': f'Unknown task "{task}". Valid tasks: {", ".join(sorted(_VALID_QUERY_TASKS))}'}), 400

    if task in ('explain', 'optimize'):
        sql = str(data.get('sql', '')).strip()
        if not sql:
            return jsonify({'error': 'sql is required'}), 400
        prompt    = _explain_prompt(sql) if task == 'explain' else _optimize_prompt(sql)
        json_mode = (task == 'optimize')
    else:  # diagnose
        step_type = str(data.get('step_type', 'unknown')).strip()
        error     = str(data.get('error', '')).strip()
        logs      = str(data.get('logs') or '').strip()
        if not error:
            return jsonify({'error': 'error is required'}), 400
        prompt    = _diagnose_prompt(step_type, error, logs)
        json_mode = False
        sql       = ''

    try:
        raw = _ollama_generate(prompt, _query_model(), json_mode=json_mode, timeout=60)
    except urllib.error.URLError:
        url = _ollama_url()
        return jsonify({'error': f'Ollama is not reachable at {url}. Is it running?'}), 503
    except Exception as exc:
        logger.exception('ai/query task=%s error: %s', task, exc)
        return jsonify({'error': str(exc)}), 500

    if task == 'optimize':
        try:
            parsed = json.loads(raw)
            result = str(parsed.get('sql', '')).strip() or sql
        except (json.JSONDecodeError, AttributeError):
            logger.warning('ai/query optimize: bad JSON from Ollama, returning raw')
            result = raw.strip() or sql
    else:
        result = raw.strip()

    return jsonify({'result': result})


@bp.post('/ai/anomaly-narrative')
@require_auth
def anomaly_narrative():
    """Generate a one-sentence plain-English explanation for a detected run anomaly."""
    data      = request.get_json() or {}
    step_name = str(data.get('step_name', '')).strip()
    metric    = str(data.get('metric', '')).strip()
    value     = data.get('value')
    mean      = data.get('mean')
    pct_diff  = data.get('pct_diff', 0)

    if not step_name or value is None or mean is None or metric not in ('rows', 'duration'):
        return jsonify({'error': 'step_name, metric (rows|duration), value, and mean are required'}), 400

    direction = 'above' if value > mean else 'below'
    abs_pct   = abs(round(pct_diff, 0))

    if metric == 'rows':
        prompt = (
            f'A data pipeline step called "{step_name}" processed {int(value):,} rows, '
            f'which is {abs_pct:.0f}% {direction} its 30-run average of {mean:,.0f} rows.\n\n'
            'Write exactly ONE plain-English sentence explaining what this anomaly likely means '
            'and what a data engineer should check. Be specific and actionable. No bullet points, no headers.'
        )
    else:
        prompt = (
            f'A data pipeline step called "{step_name}" took {int(value):,}ms to complete, '
            f'which is {abs_pct:.0f}% {direction} its 30-run average of {mean:,.0f}ms.\n\n'
            'Write exactly ONE plain-English sentence explaining what this duration anomaly likely means '
            'and what a data engineer should check. Be specific and actionable. No bullet points, no headers.'
        )

    try:
        result = _ollama_generate(prompt, _query_model(), json_mode=False, timeout=30)
    except urllib.error.URLError:
        url = _ollama_url()
        return jsonify({'error': f'Ollama is not reachable at {url}. Is it running?'}), 503
    except Exception as exc:
        logger.exception('ai/anomaly-narrative error: %s', exc)
        return jsonify({'error': str(exc)}), 500

    return jsonify({'result': result.strip()})


def _explain_prompt(sql: str) -> str:
    return (
        'You are a SQL expert. Analyze this SQL query and explain it clearly for a developer.\n\n'
        f'SQL:\n{sql}\n\n'
        'Write a structured plain-text explanation using these sections '
        '(omit any section that is not applicable):\n\n'
        'Summary\n'
        'A 2-3 sentence overview of what this query does.\n\n'
        'Tables and joins\n'
        'List the tables or views used and describe how they are joined.\n\n'
        'Filters\n'
        'Describe the WHERE clause and any other filtering logic.\n\n'
        'Aggregations\n'
        'Describe GROUP BY, HAVING, and aggregate functions (SUM, COUNT, AVG, etc.).\n\n'
        'Ordering and limits\n'
        'Describe ORDER BY, LIMIT, FETCH, or pagination clauses.\n\n'
        'Potential issues\n'
        'Flag any of these if present (skip entirely if none found):\n'
        '- No WHERE clause on what appears to be a large fact or transaction table\n'
        '- JOIN without an ON condition (cartesian product risk)\n'
        '- SELECT * (brittle — returns all columns including future ones)\n'
        '- Function applied to a column inside WHERE (may defeat an index)\n'
        '- Column or table name that looks like a possible typo\n\n'
        'Be concise and practical. Use plain text only.'
    )


def _diagnose_prompt(step_type: str, error: str, logs: str) -> str:
    logs_section = f'\nRecent logs:\n{logs[:2000]}' if logs else ''
    return (
        'You are an expert in data pipeline debugging. A pipeline step has failed.\n\n'
        f'Step type: {step_type}\n'
        f'Error:\n{error}{logs_section}\n\n'
        'In 2-4 plain-English sentences:\n'
        '1. What most likely caused this error\n'
        '2. How to fix it or work around it\n\n'
        'Be specific and actionable. No bullet points, no headers, just clear prose.'
    )


def _optimize_prompt(sql: str) -> str:
    return (
        'You are a SQL performance expert. Rewrite the query below to be more efficient.\n\n'
        f'SQL:\n{sql}\n\n'
        'Apply the following optimizations where relevant:\n'
        '- Replace correlated subqueries with JOINs or CTEs\n'
        '- Use window functions instead of self-joins for rankings or running totals\n'
        '- Rewrite WHERE clauses to be index-friendly (avoid wrapping indexed columns in functions)\n'
        '- Use EXISTS instead of IN with subqueries where appropriate\n'
        '- Replace SELECT * with explicit column references\n'
        '- Push filter conditions into subqueries or CTEs as early as possible\n\n'
        'If the query is already well-optimized, return it unchanged.\n\n'
        'Respond with ONLY valid JSON in exactly this format, no extra text:\n'
        '{"sql": "<optimized SQL here>"}'
    )
