"""AI analyze step — queries a database and passes results to an LLM for analysis."""
import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

from flowforge.steps.base import BaseStep, StepResult

logger = logging.getLogger(__name__)

_MAX_ROWS_DEFAULT = 100
_anthropic_client = None  # lazy singleton, keyed by API key


def _get_anthropic_client():
    global _anthropic_client
    try:
        import anthropic as _anthropic_mod
    except ImportError:
        raise ImportError(
            "Claude API requires: pip install anthropic  "
            "(or pip install 'flowforge[claude]')"
        )
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        raise ValueError('ANTHROPIC_API_KEY is not set')
    if _anthropic_client is None or _anthropic_client.api_key != api_key:
        _anthropic_client = _anthropic_mod.Anthropic(api_key=api_key)
    return _anthropic_client
_MAX_ROWS_HARD_CAP = 500   # never send more than this regardless of config


def _format_data(columns: list[str], rows: list[tuple]) -> str:
    """Pipe-delimited text table suitable for inclusion in an LLM prompt."""
    if not columns or not rows:
        return '(no rows returned)'
    header = ' | '.join(str(c) for c in columns)
    sep    = '-' * max(len(header), 40)
    lines  = [header, sep] + [' | '.join(str(v) for v in row) for row in rows]
    return '\n'.join(lines)


def _call_ollama(prompt: str, model: str, timeout: int = 120) -> str:
    url  = os.environ.get('OLLAMA_URL', 'http://localhost:11434').rstrip('/')
    body = json.dumps({
        'model':   model,
        'prompt':  prompt,
        'stream':  False,
        'options': {'temperature': 0.2},
    }).encode()
    req = urllib.request.Request(
        f'{url}/api/generate',
        data=body,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        result = json.loads(resp.read())
    return result.get('response', '').strip()


def _call_claude(prompt: str, model: str) -> str:
    client = _get_anthropic_client()
    message = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{'role': 'user', 'content': prompt}],
    )
    return message.content[0].text.strip()


class AiAnalyzeStep(BaseStep):
    """Run a SQL query and pass the results to an LLM for summarisation.

    The LLM response is stored as a pipeline variable (default name: ai_summary)
    so downstream email / report steps can reference it via {{ ai_summary }} or
    {{ steps.<name>.ai_summary }}.

    Config fields:
        connection_id   UUID of a saved DB connection (optional — falls back to
                        DB_HOST/DB_NAME/DB_USER/DB_PASSWORD env vars)
        query           SQL to execute (supports {{ variables }})
        prompt          Instruction sent to the LLM after the data table.
                        Supports {{ variables }}.  Default: summarise in 3 sentences.
        output_variable Name of the pipeline variable to store the result in.
                        Default: ai_summary
        provider        'ollama' (default, free, local) or 'claude' (Anthropic API)
        model           Override the default model (optional)
        max_rows        Maximum rows to include in the prompt (default 100, hard cap 500)
    """

    step_type = 'ai_analyze'

    def run(self, context: dict[str, Any]) -> StepResult:
        from flowforge.engine.context import render

        query_template = self.config.get('query', '').strip()
        if not query_template:
            return StepResult(success=False, error='ai_analyze: query is required')

        prompt_template = self.config.get('prompt', 'Summarise this dataset in 3 sentences.')
        output_var  = (self.config.get('output_variable') or 'ai_summary').strip()
        provider    = (self.config.get('provider') or 'ollama').lower().strip()
        max_rows    = min(int(self.config.get('max_rows', _MAX_ROWS_DEFAULT)), _MAX_ROWS_HARD_CAP)
        connection_id = self.config.get('connection_id', '')

        sql    = render(query_template,  context)
        prompt = render(prompt_template, context)

        # ── 1. Execute query ────────────────────────────────────────────────
        try:
            rows, columns = self._execute_query(connection_id, sql)
        except Exception as exc:
            logger.error("ai_analyze: query failed: %s", exc)
            return StepResult(success=False, error=f'Query failed: {exc}')

        total_rows = len(rows)
        data_rows  = rows[:max_rows]
        data_text  = _format_data(columns, data_rows)
        if total_rows > max_rows:
            data_text += f'\n\n[Showing first {max_rows} of {total_rows} rows]'

        logger.info(
            "ai_analyze: %d rows returned; sending %d to %s",
            total_rows, len(data_rows), provider,
        )

        # ── 2. Build prompt ─────────────────────────────────────────────────
        full_prompt = (
            'You are a data analyst. Below is the result of a SQL query.\n\n'
            f'{data_text}\n\n'
            f'Task: {prompt}'
        )

        # ── 3. Call AI provider ─────────────────────────────────────────────
        try:
            summary = self._call_provider(provider, full_prompt)
        except urllib.error.URLError as exc:
            ollama_url = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
            return StepResult(
                success=False,
                error=f'Ollama is not reachable at {ollama_url}. Is it running? ({exc})',
            )
        except Exception as exc:
            logger.error("ai_analyze: LLM call failed: %s", exc)
            return StepResult(success=False, error=f'AI call failed: {exc}')

        logger.info(
            "ai_analyze: response stored in '{{ %s }}' (%d chars)",
            output_var, len(summary),
        )

        step_log = (
            f'Provider : {provider}\n'
            f'Rows     : {total_rows} returned, {len(data_rows)} sent to LLM\n'
            f'Prompt   : {prompt[:300]}\n'
            f'Response : {summary[:500]}'
        )
        return StepResult(
            success=True,
            rows_affected=total_rows,
            ai_summary=summary,
            output_variables={output_var: summary},
            logs=step_log,
        )

    # ── helpers ────────────────────────────────────────────────────────────────

    def _execute_query(self, connection_id: str, sql: str) -> tuple[list[tuple], list[str]]:
        if connection_id:
            from flowforge.connections.factory import get_connection
            with get_connection(connection_id) as conn:
                return conn.execute_query_with_columns(sql)
        # Fallback: env-var PostgreSQL connection
        from flowforge.connections.postgres import PostgreSQLConnection
        with PostgreSQLConnection(
            host=os.environ.get('DB_HOST', ''),
            database=os.environ.get('DB_NAME', ''),
            user=os.environ.get('DB_USER', ''),
            password=os.environ.get('DB_PASSWORD', ''),
        ) as conn:
            return conn.execute_query_with_columns(sql)

    def _call_provider(self, provider: str, prompt: str) -> str:
        if provider == 'claude':
            model = self.config.get('model') or 'claude-haiku-4-5-20251001'
            return _call_claude(prompt, model)
        # Default: ollama
        model = self.config.get('model') or os.environ.get('OLLAMA_QUERY_MODEL', 'llama3.2:3b')
        return _call_ollama(prompt, model)
