"""Partitioned (bounded-memory) reconcile: same answers as one pass, a fraction of the memory."""
import math
import os
import random
import re
import subprocess
import sys
from unittest.mock import patch

import pytest

from flowforge.steps import reconcile
from flowforge.steps.reconcile import ReconcileStep, _in_partition


class FakeConn:
    """Serves rows from a function of the rendered SQL, and counts how many rows it handed out."""

    def __init__(self, rows_for, counter):
        self.rows_for, self.counter = rows_for, counter
        self.columns = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute_query_with_columns_chunked(self, sql, params=(), chunk_size=5000):
        columns, rows = self.rows_for(sql)

        def gen():
            for r in rows:
                self.counter['rows'] += 1
                yield r
        return columns, gen()


def make(config, left, right, left_cols=('k',), right_cols=('k',), left_fn=None, right_fn=None):
    """A step whose connections serve ``left``/``right`` (or ``left_fn(sql)``/``right_fn(sql)``)."""
    counter = {'rows': 0}
    cfg = {'left_connection_id': 'L', 'right_connection_id': 'R',
           'left_query': 'SELECT k FROM l', 'right_query': 'SELECT k FROM r', **config}
    sources = {'L': left_fn or (lambda sql: (list(left_cols), left)),
               'R': right_fn or (lambda sql: (list(right_cols), right))}
    step = ReconcileStep('recon', cfg)
    step._open = lambda cid: FakeConn(sources[cid], counter)
    return step, counter


def run(config, left, right, **kw):
    step, counter = make(config, left, right, **kw)
    return step.run({'steps': {}}), counter


def dataset(n=2000, seed=3):
    """Left/right with overlap, one-sided keys, value drift and duplicates."""
    rng = random.Random(seed)
    keys = [f'1555{i:07d}' for i in range(n)]
    left = [(k, rng.choice([10, 25, 60])) for k in keys if rng.random() > 0.05]
    right = [(k, v + (5 if rng.random() < 0.04 else 0)) for k, v in left if rng.random() > 0.05]
    right += [(f'9999{i:07d}', 10) for i in range(40)]               # right-only
    right += right[:15]                                              # duplicates
    left += left[:10]
    rng.shuffle(left)
    rng.shuffle(right)
    return left, right


VALUES = {'compare': 'values', 'sample_size': 1000}


def _norm(result):
    v = {k.split('_', 1)[1]: x for k, x in result.output_variables.items()}
    v.pop('passes')
    return v, sorted((r['issue'], r['key']) for r in result.rows)


# -- same answers as one pass ------------------------------------------------------------

@pytest.mark.parametrize('n', [2, 3, 7, 16])
def test_partitioned_python_mode_matches_a_single_pass(n):
    left, right = dataset()
    base, _ = run(VALUES, left, right, left_cols=('k', 'v'), right_cols=('k', 'v'))
    part, _ = run({**VALUES, 'partitions': n}, left, right, left_cols=('k', 'v'), right_cols=('k', 'v'))
    assert base.success and part.success
    assert _norm(part) == _norm(base)
    assert part.rows_affected == base.rows_affected > 0
    assert part.output_variables['recon_passes'] == n


def test_keys_mode_matches_too():
    left, right = dataset()
    keys_l, keys_r = [(k,) for k, _ in left], [(k,) for k, _ in right]
    base, _ = run({'sample_size': 1000}, keys_l, keys_r)
    part, _ = run({'sample_size': 1000, 'partitions': 5}, keys_l, keys_r)
    assert _norm(part) == _norm(base)


# -- the memory bound --------------------------------------------------------------------

def test_each_pass_holds_only_a_fraction_of_the_left_keys():
    left, right = dataset(4000)
    sizes = []
    original = ReconcileStep._only_left

    def spy(self, cfg, left_map, seen, sample):
        sizes.append(len(left_map))
        return original(self, cfg, left_map, seen, sample)

    step, _ = make({**VALUES, 'partitions': 8}, left, right, left_cols=('k', 'v'), right_cols=('k', 'v'))
    with patch.object(ReconcileStep, '_only_left', spy):
        assert step.run({'steps': {}}).success
    distinct = len({k for k, _ in left})
    assert len(sizes) == 8 and sum(sizes) == distinct
    assert max(sizes) < distinct / 8 * 1.3       # roughly even; nothing close to the whole side


def test_max_rows_is_per_pass_so_partitions_make_a_too_big_side_fit():
    left, right = dataset(1500)
    left_k, right_k = [(k,) for k, _ in left], [(k,) for k, _ in right]
    distinct = len({k for k, in left_k})
    cfg = {'max_rows': distinct // 4, 'sample_size': 1000}
    one, _ = run(cfg, left_k, right_k)
    assert not one.success and 'max_rows' in one.error
    many, _ = run({**cfg, 'partitions': 8}, left_k, right_k)
    assert many.success, many.error
    whole, _ = run({'sample_size': 1000}, left_k, right_k)
    assert _norm(many) == _norm(whole)


# -- python vs sql mode: the time/memory trade -------------------------------------------

def _sql_source(rows, with_value):
    """Rows served as a database would: filtered by the rendered ``MOD(k, N) = i`` predicate."""
    def fn(sql):
        m = re.search(r'MOD\(k, (\d+)\) = (\d+)', sql)
        kept = [r for r in rows if not m or int(r[0]) % int(m.group(1)) == int(m.group(2))]
        return (['k', 'v'] if with_value else ['k']), kept
    return fn


def test_sql_mode_reads_each_row_once_while_python_mode_rereads_everything():
    left = [(i, i % 7) for i in range(1, 3001) if i % 11]
    right = [(i, i % 7) for i in range(1, 3001) if i % 13]
    n = 6
    pred = 'WHERE MOD(k, {{ partitions }}) = {{ partition_index }}'
    sql_cfg = {'compare': 'values', 'sample_size': 1000, 'partitions': n, 'partition_mode': 'sql',
               'left_query': f'SELECT k, v FROM l {pred}', 'right_query': f'SELECT k, v FROM r {pred}'}
    base, _ = run({'compare': 'values', 'sample_size': 1000}, left, right, left_cols=('k', 'v'), right_cols=('k', 'v'))
    sql_res, sql_counter = make(sql_cfg, None, None, left_fn=_sql_source(left, True), right_fn=_sql_source(right, True))
    r_sql = sql_res.run({'steps': {}})
    assert r_sql.success, r_sql.error
    assert _norm(r_sql) == _norm(base)
    assert sql_counter['rows'] == len(left) + len(right)                    # each row crossed the wire once

    py_cfg = {'compare': 'values', 'sample_size': 1000, 'partitions': n}
    r_py, py_counter = run(py_cfg, left, right, left_cols=('k', 'v'), right_cols=('k', 'v'))
    assert _norm(r_py) == _norm(base)
    assert py_counter['rows'] == n * (len(left) + len(right))               # the documented cost of python mode


def test_sql_mode_refuses_queries_that_do_not_filter_on_the_partition():
    """Otherwise every pass reads everything and every count comes out N times too big."""
    r, counter = run({'partitions': 4, 'partition_mode': 'sql'}, [('a',)], [('a',)])
    assert not r.success and 'partition_index' in r.error and 'left_query' in r.error
    assert counter['rows'] == 0                                              # refused before reading anything
    ok, _ = run({'partitions': 4, 'partition_mode': 'sql',
                 'left_query': 'SELECT k FROM l WHERE {{ partition_index }} >= 0',
                 'right_query': 'SELECT k FROM r'}, [('a',)], [('a',)])
    assert not ok.success and 'right_query' in ok.error                      # each side is checked


def test_sql_mode_with_a_single_pass_needs_no_predicate():
    r, _ = run({'partition_mode': 'sql'}, [('a',), ('b',)], [('b',)])
    assert r.success and r.output_variables['recon_only_left'] == 1


# -- sampling, config and the hash -------------------------------------------------------

def test_sample_size_caps_each_category_across_all_passes():
    left = [(f'L{i}',) for i in range(200)]
    right = [(f'R{i}',) for i in range(200)]
    r, _ = run({'partitions': 4, 'sample_size': 3}, left, right)
    assert r.output_variables['recon_only_left'] == 200 and r.output_variables['recon_only_right'] == 200
    by_issue = {}
    for row in r.rows:
        by_issue[row['issue']] = by_issue.get(row['issue'], 0) + 1
    assert by_issue == {'only_in_left': 3, 'only_in_right': 3}


@pytest.mark.parametrize('bad,field', [
    ({'partitions': 0}, 'partitions'), ({'partitions': 257}, 'partitions'), ({'partitions': 'x'}, 'partitions'),
    ({'partitions': 2, 'partition_mode': 'nope'}, 'partition_mode'),
])
def test_invalid_partition_config_is_rejected(bad, field):
    r, counter = run(bad, [('a',)], [('a',)])
    assert not r.success and field in r.error and counter['rows'] == 0


def test_every_key_belongs_to_exactly_one_partition():
    keys = [f'key-{i}' for i in range(5000)]
    for n in (2, 5, 16):
        owners = [sum(_in_partition(k, (i, n)) for i in range(n)) for k in keys]
        assert set(owners) == {1}
        sizes = [sum(_in_partition(k, (i, n)) for k in keys) for i in range(n)]
        assert max(sizes) < math.ceil(len(keys) / n) * 1.25                  # reasonably balanced


def test_partition_assignment_does_not_depend_on_the_process_hash_seed():
    """hash() is randomized per process; a split that used it would differ between runs and sides."""
    code = ("from flowforge.steps.reconcile import _in_partition;"
            "print([i for i in range(40) if _in_partition(f'1555{i:07d}', (1, 4))])")
    outs = set()
    for seed in ('1', '2', '12345'):
        env = {**os.environ, 'PYTHONHASHSEED': seed}
        outs.add(subprocess.run([sys.executable, '-I', '-c', code], capture_output=True, text=True,
                                env=env, check=True, cwd=os.path.dirname(os.path.dirname(reconcile.__file__))
                                ).stdout.strip())
    assert len(outs) == 1
