"""Reconciliation step — compare keyed results from two connections.

A single ``db_query`` can only join tables that live in one database, but the
systems a revenue-assurance audit compares (CRM, billing, HLR/HSS) normally sit
in different ones. This step runs one query per side and diffs the results:

* keys present on only one side ("orphans"), and
* optionally, keys on both sides whose value column disagrees beyond a tolerance.

Memory model: the *left* result is held in memory as ``{key: value}`` and the
*right* result is streamed in chunks, so peak memory is roughly one side, not
both (about 180 bytes per distinct left key, see docs/benchmark.md). ``max_rows``
caps each side; exceeding it fails the step with a clear message instead of
exhausting memory. Heavy lifting (filters, in-flight provisioning windows,
aggregation) belongs in the two queries, which run inside the source databases.

Bounded memory for very large tables: ``partitions: N`` runs the comparison as N
independent passes over disjoint subsets of the keys, so each pass holds about 1/N
of the left side. Counts add up exactly across passes (the subsets do not overlap)
and ``max_rows`` applies per pass. Two ways to split:

* ``partition_mode: python`` (default) - every pass reads both full result sets and keeps
  only keys whose ``crc32(normalized key) % N`` equals the pass number. Works across any
  mix of databases with no SQL changes, but each pass re-reads everything: memory drops,
  time rises roughly N-fold.
* ``partition_mode: sql`` - the queries receive ``{{ partition_index }}`` and
  ``{{ partitions }}`` and must filter in SQL (e.g. ``MOD(CAST(msisdn AS BIGINT), {{ partitions }})
  = {{ partition_index }}``), so each pass reads only about 1/N of the rows: memory *and*
  total time stay flat. The predicate must select the same keys on both sides. That
  cannot be verified here, so a predicate that differs between sides gives wrong counts;
  the step only checks that both queries reference ``partition_index``.

Only counts and a capped sample of offending keys are returned. The sample
contains raw key values unless ``tokenize_keys`` is on (keyed HMAC tokens instead); set
``sample_size`` to 0 to return counts only.
"""
import logging
import re
import zlib
from decimal import Decimal
from typing import Any

from flowforge.steps.base import BaseStep, StepResult
from flowforge.tokenization import TOKEN_KINDS, TokenizationError, check_ready, tokenize

logger = logging.getLogger(__name__)

_PREFIX_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
_VALID_COMPARE = {'keys', 'values'}
_VALID_CASE = {'none', 'upper', 'lower'}
_VALID_PARTITION_MODE = {'python', 'sql'}
_MAX_PARTITIONS = 256
_DEFAULT_MAX_ROWS = 5_000_000
_DEFAULT_SAMPLE = 20
_MAX_SAMPLE = 1000
_CHUNK = 5000


class ReconcileError(Exception):
    """A configuration or data problem that should fail the step with a message."""


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float, Decimal)) and not isinstance(v, bool)


def normalize_key(value: Any, trim: bool, case: str) -> str:
    """Canonical string form of a key so ``123`` (NUMBER) equals ``'123'`` (VARCHAR)."""
    if value is None:
        return ''
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    elif isinstance(value, Decimal) and value == value.to_integral_value():
        value = int(value)
    s = str(value)
    if trim:
        s = s.strip()
    if case == 'upper':
        s = s.upper()
    elif case == 'lower':
        s = s.lower()
    return s


def _display(value: Any) -> Any:
    """JSON-safe representation for the result sample."""
    if value is None or isinstance(value, (int, float, str, bool)):
        return value
    return str(value)


def _in_partition(key: str, part: tuple[int, int]) -> bool:
    """Whether ``key`` (already normalized) belongs to pass ``part[0]`` of ``part[1]``.

    crc32, not hash(): Python's hash() is randomized per process, and the split must be the same
    on the left and right side and stable between runs.
    """
    return zlib.crc32(key.encode('utf-8')) % part[1] == part[0]


def _shown(cfg: dict, key: str) -> str:
    """The key as it may leave the step: a keyed token when ``tokenize_keys`` is on."""
    return tokenize(key, cfg['token_kind']) if cfg['tokenize'] else key


def values_differ(left: Any, right: Any, tolerance: float, tolerance_pct: float,
                  trim: bool, case: str) -> bool:
    if left is None or right is None:
        return left is not right
    if _is_number(left) and _is_number(right):
        diff = abs(float(left) - float(right))
        if diff <= tolerance:
            return False
        if tolerance_pct and left != 0 and diff <= abs(float(left)) * tolerance_pct / 100.0:
            return False
        return True
    return normalize_key(left, trim, case) != normalize_key(right, trim, case)


class ReconcileStep(BaseStep):
    """Compare keyed query results from two connections.

    Config fields:
        left_connection_id / right_connection_id   connection IDs (required)
        left_query / right_query                   SQL, first column = key,
                                                   second column = value (compare: values)
        left_label / right_label                   names used in logs (default left/right)
        compare           'keys' (default) | 'values'
        tolerance         absolute numeric tolerance for compare: values (default 0)
        tolerance_pct     relative tolerance, percent of the left value (default 0)
        key_trim          strip whitespace from keys (default true)
        key_case          'none' (default) | 'upper' | 'lower'
        sample_size       cap on offending keys returned per category (default 20, 0 = none)
        tokenize_keys     replace sampled keys with keyed HMAC tokens (default false); fails
                          the step if no key is configured. Matching is unaffected. Only keys
                          are tokenized — never select PII as the value column
        token_kind        'msisdn' (default) | 'imsi' | 'generic' — see flowforge/tokenization.py
        max_rows          cap on distinct keys per side, per pass (default 5,000,000)
        partitions        number of passes over disjoint key subsets (default 1, max 256);
                          bounds memory to about 1/N of the left side - see module docstring
        partition_mode    'python' (default; filters in Python, time rises ~N-fold) | 'sql'
                          (queries use {{ partition_index }} / {{ partitions }}; time stays flat)
        output_prefix     prefix for output variables (default 'recon')
    """

    step_type = 'reconcile'

    def run(self, context: dict[str, Any]) -> StepResult:
        try:
            cfg = self._parse_config()
        except ReconcileError as e:
            return StepResult(success=False, error=f'reconcile: {e}')

        if cfg['tokenize']:
            try:
                check_ready()   # fail before any query runs; never fall back to raw keys
            except TokenizationError as e:
                return StepResult(success=False, error=f'reconcile: tokenize_keys is on but {e}')

        from flowforge.engine.context import render_sql
        passes = cfg['partitions']
        totals = {'left': 0, 'left_dups': 0, 'only_left': 0, 'right': 0, 'matched': 0,
                  'only_right': 0, 'mismatched': 0, 'right_dups': 0}
        # one shared sample, so sample_size caps each category across all passes
        sample: dict[str, list[dict]] = {'only_right': [], 'mismatched': [], 'only_left': []}

        try:
            for k in range(passes):
                ctx = {**context, 'partition_index': k, 'partitions': passes}
                left_sql = render_sql(self.config['left_query'], ctx)
                right_sql = render_sql(self.config['right_query'], ctx)
                # in 'python' mode this pass keeps only its own keys; in 'sql' mode (and for a
                # single pass) the queries have already selected them, so nothing is filtered here
                part = (k, passes) if passes > 1 and cfg['partition_mode'] == 'python' else None
                left, left_dups = self._load_left(cfg, left_sql, part)
                counts, seen = self._stream_right(cfg, left, right_sql, part, sample)
                totals['only_left'] += self._only_left(cfg, left, seen, sample)
                totals['left'] += len(left)
                totals['left_dups'] += left_dups
                for name in ('right', 'matched', 'only_right', 'mismatched', 'right_dups'):
                    totals[name] += counts[name]
                del left, seen          # free this partition before the next one is loaded
        except ReconcileError as e:
            return StepResult(success=False, error=f'reconcile: {e}')
        except Exception as e:
            logger.exception('Reconcile step failed')
            return StepResult(success=False, error=f'reconcile: {e}')
        return self._finish(cfg, totals, sample)

    # -- configuration ------------------------------------------------------

    def _parse_config(self) -> dict[str, Any]:
        c = self.config
        for field in ('left_connection_id', 'right_connection_id', 'left_query', 'right_query'):
            if not str(c.get(field) or '').strip():
                raise ReconcileError(f'{field} is required')
        compare = str(c.get('compare', 'keys')).lower()
        if compare not in _VALID_COMPARE:
            raise ReconcileError(f"compare must be one of: {', '.join(sorted(_VALID_COMPARE))}")
        case = str(c.get('key_case', 'none')).lower()
        if case not in _VALID_CASE:
            raise ReconcileError(f"key_case must be one of: {', '.join(sorted(_VALID_CASE))}")
        token_kind = str(c.get('token_kind', 'msisdn')).lower()
        if token_kind not in TOKEN_KINDS:
            raise ReconcileError(f"token_kind must be one of: {', '.join(TOKEN_KINDS)}")
        prefix = str(c.get('output_prefix') or 'recon')
        if not _PREFIX_RE.match(prefix):
            raise ReconcileError('output_prefix must be a valid variable name (letters, digits, underscore)')
        try:
            tolerance = float(c.get('tolerance', 0) or 0)
            tolerance_pct = float(c.get('tolerance_pct', 0) or 0)
            sample_size = int(c.get('sample_size', _DEFAULT_SAMPLE))
            max_rows = int(c.get('max_rows', _DEFAULT_MAX_ROWS))
        except (TypeError, ValueError):
            raise ReconcileError('tolerance, tolerance_pct, sample_size and max_rows must be numbers') from None
        if tolerance < 0 or tolerance_pct < 0:
            raise ReconcileError('tolerance and tolerance_pct must not be negative')
        if max_rows < 1:
            raise ReconcileError('max_rows must be at least 1')
        partition_mode = str(c.get('partition_mode', 'python')).lower()
        if partition_mode not in _VALID_PARTITION_MODE:
            raise ReconcileError(f"partition_mode must be one of: {', '.join(sorted(_VALID_PARTITION_MODE))}")
        try:
            partitions = int(c.get('partitions', 1))
        except (TypeError, ValueError):
            raise ReconcileError('partitions must be a whole number') from None
        if not 1 <= partitions <= _MAX_PARTITIONS:
            raise ReconcileError(f'partitions must be between 1 and {_MAX_PARTITIONS}')
        if partitions > 1 and partition_mode == 'sql':
            # without this guard every pass would read everything and every count would be N times too big
            for field in ('left_query', 'right_query'):
                if 'partition_index' not in str(c[field]):
                    raise ReconcileError(
                        f"partition_mode 'sql' needs {field} to filter on {{{{ partition_index }}}} "
                        "(and {{ partitions }}); otherwise every pass reads all rows"
                    )
        return {
            'partitions': partitions,
            'partition_mode': partition_mode,
            'compare': compare,
            'trim': bool(c.get('key_trim', True)),
            'case': case,
            'prefix': prefix,
            'tokenize': bool(c.get('tokenize_keys', False)),
            'token_kind': token_kind,
            'tolerance': tolerance,
            'tolerance_pct': tolerance_pct,
            'sample_size': max(0, min(sample_size, _MAX_SAMPLE)),
            'max_rows': max_rows,
            'left_label': str(c.get('left_label') or 'left'),
            'right_label': str(c.get('right_label') or 'right'),
        }

    # -- data loading -------------------------------------------------------

    def _open(self, conn_id: str):
        from flowforge.connections.factory import get_connection
        return get_connection(conn_id)

    def _check_columns(self, cfg: dict, columns: list[str], side: str) -> None:
        need = 2 if cfg['compare'] == 'values' else 1
        if len(columns) < need:
            raise ReconcileError(
                f"{side} query must return at least {need} column(s) "
                f"(key{', value' if need == 2 else ''}); it returned {len(columns)}"
            )

    def _load_left(self, cfg: dict, sql: str, part: tuple[int, int] | None = None):
        left: dict[str, Any] = {}
        dups = 0
        with self._open(self.config['left_connection_id']) as conn:
            columns, rows = conn.execute_query_with_columns_chunked(sql, (), _CHUNK)
            self._check_columns(cfg, columns, cfg['left_label'])
            for row in rows:
                key = normalize_key(row[0], cfg['trim'], cfg['case'])
                if part is not None and not _in_partition(key, part):
                    continue
                if key in left:
                    dups += 1
                    continue
                if len(left) >= cfg['max_rows']:
                    raise ReconcileError(
                        f"{cfg['left_label']} query returned more than max_rows={cfg['max_rows']} "
                        'distinct keys; narrow the query (aggregate or filter in SQL) or raise max_rows'
                    )
                left[key] = row[1] if cfg['compare'] == 'values' else None
        return left, dups

    def _stream_right(self, cfg: dict, left: dict[str, Any], sql: str, part: tuple[int, int] | None,
                      sample: dict[str, list[dict]]):
        compare_values = cfg['compare'] == 'values'
        seen: set[str] = set()
        counts = {'right': 0, 'matched': 0, 'only_right': 0, 'mismatched': 0, 'right_dups': 0}
        cap = cfg['sample_size']
        with self._open(self.config['right_connection_id']) as conn:
            columns, rows = conn.execute_query_with_columns_chunked(sql, (), _CHUNK)
            self._check_columns(cfg, columns, cfg['right_label'])
            for row in rows:
                key = normalize_key(row[0], cfg['trim'], cfg['case'])
                if part is not None and not _in_partition(key, part):
                    continue
                if key in seen:
                    counts['right_dups'] += 1
                    continue
                if len(seen) >= cfg['max_rows']:
                    raise ReconcileError(
                        f"{cfg['right_label']} query returned more than max_rows={cfg['max_rows']} "
                        'distinct keys; narrow the query (aggregate or filter in SQL) or raise max_rows'
                    )
                seen.add(key)
                counts['right'] += 1
                if key not in left:
                    counts['only_right'] += 1
                    if len(sample['only_right']) < cap:
                        sample['only_right'].append({
                            'issue': 'only_in_right', 'key': _shown(cfg, key),
                            'left_value': None,
                            'right_value': _display(row[1]) if compare_values else None,
                        })
                    continue
                counts['matched'] += 1
                if compare_values and values_differ(
                    left[key], row[1], cfg['tolerance'], cfg['tolerance_pct'], cfg['trim'], cfg['case'],
                ):
                    counts['mismatched'] += 1
                    if len(sample['mismatched']) < cap:
                        sample['mismatched'].append({
                            'issue': 'value_mismatch', 'key': _shown(cfg, key),
                            'left_value': _display(left[key]), 'right_value': _display(row[1]),
                        })
        return counts, seen

    # -- result -------------------------------------------------------------

    def _only_left(self, cfg, left: dict[str, Any], seen: set[str], sample: dict[str, list[dict]]) -> int:
        """Count (and sample) this pass's left keys that the right side never produced."""
        only_left = 0
        for key, value in left.items():
            if key in seen:
                continue
            only_left += 1
            if len(sample['only_left']) < cfg['sample_size']:
                sample['only_left'].append({
                    'issue': 'only_in_left', 'key': _shown(cfg, key),
                    'left_value': _display(value), 'right_value': None,
                })
        return only_left

    def _finish(self, cfg, t: dict[str, int], sample: dict[str, list[dict]]) -> StepResult:
        discrepancies = t['only_left'] + t['only_right'] + t['mismatched']
        p = cfg['prefix']
        output_vars = {
            f'{p}_left_count': t['left'],
            f'{p}_right_count': t['right'],
            f'{p}_matched': t['matched'],
            f'{p}_only_left': t['only_left'],
            f'{p}_only_right': t['only_right'],
            f'{p}_mismatched': t['mismatched'],
            f'{p}_discrepancies': discrepancies,
            f'{p}_left_duplicates': t['left_dups'],
            f'{p}_right_duplicates': t['right_dups'],
            f'{p}_passes': cfg['partitions'],
        }
        rows = sample['only_left'] + sample['only_right'] + sample['mismatched']
        from flowforge.steps.db_query import _render_table_html
        logs = (
            f"Reconciled {cfg['left_label']} ({t['left']} keys) vs {cfg['right_label']} "
            f"({t['right']} keys): {t['matched']} matched, "
            f"{t['only_left']} only in {cfg['left_label']}, {t['only_right']} only in {cfg['right_label']}"
            + (f", {t['mismatched']} value mismatches" if cfg['compare'] == 'values' else '')
            + f". Duplicate keys ignored: {t['left_dups']} left, {t['right_dups']} right."
            + (f" Compared in {cfg['partitions']} {cfg['partition_mode']}-partitioned passes."
               if cfg['partitions'] > 1 else '')
        )
        logger.info(logs)
        return StepResult(
            success=True,
            rows_affected=discrepancies,
            logs=logs,
            output_variables=output_vars,
            rows=rows,
            table_html=_render_table_html(rows),
        )
