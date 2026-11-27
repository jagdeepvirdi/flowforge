"""Pure logic of the volume benchmark and the streaming dataset generator (no database)."""
import pytest

from flowforge.demo import bench
from flowforge.demo.telecom import generate, generate_batches

# -- generator ----------------------------------------------------------------------------

@pytest.mark.parametrize('batch_size', [1, 7, 333, 5000, 10_000_000])
def test_batched_generation_equals_single_pass(batch_size):
    ds = generate(1500, 0.03, 0.01, seed=9)
    truth, batches = generate_batches(1500, 0.03, 0.01, seed=9, batch_size=batch_size)
    crm, billing, hlr = [], [], []
    for c, b, h in batches:
        assert len(c) <= batch_size
        crm += c
        billing += b
        hlr += h
    assert (crm, billing, hlr) == (ds.crm, ds.billing, ds.hlr)
    assert truth.counts == ds.truth.counts and truth.keys == ds.truth.keys


def test_ground_truth_is_known_before_any_row_is_generated():
    truth, batches = generate_batches(1000, 0.02, 0.005)
    assert truth.counts['active_unbilled'] == 20 and truth.counts['in_flight'] == 5
    assert next(iter(batches))[0]            # and rows still come out afterwards


def test_batch_size_validated():
    with pytest.raises(ValueError):
        generate_batches(10, batch_size=0)


# -- queries and expectations -------------------------------------------------------------

def test_queries_use_the_dialect_of_the_system_they_run_in():
    pg = bench.audit_queries(bench.LAYOUTS['pg'])
    ora = bench.audit_queries(bench.LAYOUTS['oracle'])
    assert "now() - interval '48 hours'" in pg['crm_keys'] and 'SYSTIMESTAMP' not in pg['crm_keys']
    assert "SYSTIMESTAMP - INTERVAL '48' HOUR" in ora['crm_keys'] and 'now()' not in ora['crm_keys']
    # cross layout: the CRM lives in PostgreSQL, so its filter is PostgreSQL's even though billing is Oracle
    cross = bench.audit_queries(bench.LAYOUTS['cross'])
    assert 'now()' in cross['crm_values'] and 'SYSTIMESTAMP' not in cross['crm_values']


def test_no_template_marker_is_left_in_a_query():
    for layout in bench.LAYOUTS.values():
        for sql in bench.audit_queries(layout).values():
            assert '@' not in sql


def test_layouts_place_every_table_somewhere_known():
    for layout in bench.LAYOUTS.values():
        assert set(layout) == {'crm', 'billing', 'hlr'}
        assert set(layout.values()) <= {'pg', 'oracle'}
    assert set(bench.LAYOUTS['cross'].values()) == {'pg', 'oracle'}      # the point of that layout


def test_expected_counts_map_planted_categories_to_findings():
    counts = {'active_unbilled': 10, 'billed_unprovisioned': 20, 'status_mismatch': 30,
              'charge_mismatch': 40, 'in_flight': 5}
    want = bench.expected_counts(counts)
    assert want['audit_crm_vs_billing'] == {'only_left': 10, 'only_right': 0, 'mismatched': 40}
    assert want['audit_crm_vs_hlr'] == {'only_left': 20, 'only_right': 30, 'mismatched': 0}
    assert 5 not in {v for d in want.values() for v in d.values()}       # in-flight is never expected


# -- summary and measurement --------------------------------------------------------------

def _run(layout, size, seconds, correct=True, rss=100.0):
    return {'layout': layout, 'size': size, 'total_seconds': seconds, 'peak_rss_mb': rss, 'correct': correct}


def test_summary_reports_best_median_worst_and_ignores_incorrect_runs():
    rows = bench.summarize([_run('pg', 1000, 3.0), _run('pg', 1000, 1.0), _run('pg', 1000, 2.0),
                            _run('pg', 1000, 0.1, correct=False),            # a fast wrong answer must not win
                            _run('oracle', 1000, 5.0)])
    pg = next(r for r in rows if r['layout'] == 'pg')
    assert (pg['best_s'], pg['median_s'], pg['worst_s']) == (1.0, 2.0, 3.0)
    assert (pg['runs'], pg['correct_runs']) == (4, 3)
    assert next(r for r in rows if r['layout'] == 'oracle')['runs'] == 1


def test_summary_with_no_correct_runs_has_no_timings():
    row = bench.summarize([_run('pg', 10, 1.0, correct=False)])[0]
    assert row['best_s'] is None and row['median_s'] is None and row['correct_runs'] == 0


def test_peak_rss_tracks_real_allocation():
    before = bench.peak_rss_mb()
    assert before > 5
    block = bytearray(120 * 1024 * 1024)
    block[::4096] = b'x' * len(block[::4096])          # touch pages so they are resident
    assert bench.peak_rss_mb() - before > 100
    del block


def test_missing_configuration_names_the_variable_without_leaking_values(monkeypatch):
    monkeypatch.delenv('FLOWFORGE_BENCH_PG_DSN', raising=False)
    with pytest.raises(SystemExit) as e:
        bench._pg_dsn()
    assert 'FLOWFORGE_BENCH_PG_DSN' in str(e.value)
    monkeypatch.setenv('FLOWFORGE_BENCH_PG_DSN', 'postgresql://u:topsecret@h/db')
    assert bench._pg_dsn().endswith('/db')
