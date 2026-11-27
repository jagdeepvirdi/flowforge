"""Unit tests for the reconcile step (no database needed — connections are faked)."""
from decimal import Decimal
from unittest.mock import patch

from flowforge.steps.reconcile import ReconcileStep, normalize_key, values_differ


class FakeConn:
    def __init__(self, columns, rows):
        self.columns, self.rows = columns, rows

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute_query_with_columns_chunked(self, sql, params=(), chunk_size=5000):
        return self.columns, iter(self.rows)


def run(config, left, right, left_cols=('k',), right_cols=('k',)):
    cfg = {
        'left_connection_id': 'L', 'right_connection_id': 'R',
        'left_query': 'SELECT k FROM l', 'right_query': 'SELECT k FROM r',
        **config,
    }
    conns = {'L': FakeConn(list(left_cols), left), 'R': FakeConn(list(right_cols), right)}
    step = ReconcileStep('recon', cfg)
    with patch.object(ReconcileStep, '_open', lambda self, cid: conns[cid]):
        return step.run({'steps': {}})


def test_key_sets_find_orphans_on_both_sides():
    r = run({}, [('a',), ('b',), ('c',)], [('b',), ('c',), ('d',)])
    assert r.success
    v = r.output_variables
    assert (v['recon_only_left'], v['recon_only_right'], v['recon_matched']) == (1, 1, 2)
    assert v['recon_discrepancies'] == r.rows_affected == 2
    assert {(x['issue'], x['key']) for x in r.rows} == {('only_in_left', 'a'), ('only_in_right', 'd')}


def test_identical_sets_have_no_discrepancies():
    r = run({}, [('a',), ('b',)], [('b',), ('a',)])
    assert r.rows_affected == 0 and r.rows == [] and r.table_html == ''


def test_numeric_and_string_keys_match_after_normalization():
    r = run({}, [(Decimal('4915'),), (4916.0,)], [('4915',), (' 4916 ',)])
    assert r.output_variables['recon_discrepancies'] == 0


def test_key_case_option():
    assert run({}, [('Ab',)], [('aB',)]).rows_affected == 2
    assert run({'key_case': 'lower'}, [('Ab',)], [('aB',)]).rows_affected == 0


def test_duplicates_are_counted_not_double_matched():
    r = run({}, [('a',), ('a',), ('b',)], [('a',), ('a',), ('a',)])
    v = r.output_variables
    assert v['recon_left_duplicates'] == 1 and v['recon_right_duplicates'] == 2
    assert v['recon_matched'] == 1 and v['recon_only_left'] == 1


def test_value_compare_flags_mismatch_and_honours_tolerance():
    left = [('a', 100), ('b', 100), ('c', 'ACTIVE')]
    right = [('a', 100.4), ('b', 105), ('c', 'SUSPENDED')]
    strict = run({'compare': 'values'}, left, right, ('k', 'v'), ('k', 'v'))
    assert strict.output_variables['recon_mismatched'] == 3
    loose = run({'compare': 'values', 'tolerance': 0.5}, left, right, ('k', 'v'), ('k', 'v'))
    assert {x['key'] for x in loose.rows} == {'b', 'c'}
    pct = run({'compare': 'values', 'tolerance_pct': 5}, left, right, ('k', 'v'), ('k', 'v'))
    assert {x['key'] for x in pct.rows} == {'c'}


def test_null_values_only_equal_each_other():
    assert not values_differ(None, None, 0, 0, True, 'none')
    assert values_differ(None, 'x', 0, 0, True, 'none')


def test_sample_is_capped_but_counts_are_exact():
    left = [(f'k{i}',) for i in range(50)]
    r = run({'sample_size': 5}, left, [])
    assert r.output_variables['recon_only_left'] == 50
    assert len(r.rows) == 5
    assert run({'sample_size': 0}, left, []).rows == []


def test_max_rows_fails_clearly_instead_of_exhausting_memory():
    r = run({'max_rows': 2}, [('a',), ('b',), ('c',)], [])
    assert not r.success and 'max_rows' in r.error


def test_missing_value_column_fails_in_values_mode():
    r = run({'compare': 'values'}, [('a',)], [('a',)])
    assert not r.success and 'at least 2 column' in r.error


def test_custom_output_prefix_and_validation():
    r = run({'output_prefix': 'hlr'}, [('a',)], [])
    assert r.output_variables['hlr_only_left'] == 1
    bad = run({'output_prefix': 'x; drop'}, [('a',)], [])
    assert not bad.success and 'output_prefix' in bad.error


def test_required_config_and_options_validated():
    step = ReconcileStep('r', {'left_connection_id': 'L'})
    res = step.run({'steps': {}})
    assert not res.success and 'right_connection_id' in res.error
    assert not run({'compare': 'nope'}, [], []).success
    assert not run({'tolerance': -1}, [], []).success


def test_connection_error_becomes_failed_result():
    step = ReconcileStep('r', {'left_connection_id': 'L', 'right_connection_id': 'R',
                               'left_query': 'x', 'right_query': 'y'})
    with patch.object(ReconcileStep, '_open', side_effect=RuntimeError('boom')):
        res = step.run({'steps': {}})
    assert not res.success and 'boom' in res.error


def test_normalize_key_none_is_empty_string():
    assert normalize_key(None, True, 'none') == ''
