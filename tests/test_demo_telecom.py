"""Synthetic telecom dataset: determinism, planted counts, agreement with the reconcile step."""
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from flowforge.demo.telecom import PROVISIONING_WINDOW_HOURS, generate
from flowforge.steps.reconcile import ReconcileStep


def test_deterministic_for_same_seed():
    a, b = generate(2000, seed=7), generate(2000, seed=7)
    assert a.crm == b.crm and a.billing == b.billing and a.hlr == b.hlr
    assert generate(2000, seed=8).crm != a.crm


def test_planted_counts_match_rates():
    ds = generate(10_000, orphan_rate=0.02, in_flight_rate=0.005)
    assert ds.truth.counts == {'active_unbilled': 200, 'billed_unprovisioned': 200,
                               'status_mismatch': 200, 'charge_mismatch': 200, 'in_flight': 50}
    assert len({r[0] for r in ds.crm}) == 10_000


def test_zero_rates_give_clean_data():
    ds = generate(500, orphan_rate=0, in_flight_rate=0)
    assert {r[0] for r in ds.crm} == {r[0] for r in ds.billing} == {r[0] for r in ds.hlr}


def test_invalid_rates_rejected():
    with pytest.raises(ValueError):
        generate(100, orphan_rate=0.5)
    with pytest.raises(ValueError):
        generate(0)


class FakeConn:
    def __init__(self, columns, rows):
        self.columns, self.rows = columns, rows

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute_query_with_columns_chunked(self, sql, params=(), chunk_size=5000):
        return self.columns, iter(self.rows)


def _recon(left_rows, right_rows):
    conns = {'L': FakeConn(['k'], left_rows), 'R': FakeConn(['k'], right_rows)}
    step = ReconcileStep('r', {'left_connection_id': 'L', 'right_connection_id': 'R',
                               'left_query': 'x', 'right_query': 'y', 'sample_size': 0})
    with patch.object(ReconcileStep, '_open', lambda self, cid: conns[cid]):
        return step.run({'steps': {}})


def test_reconcile_recovers_planted_orphans_and_ignores_in_flight():
    now = datetime(2026, 1, 1)
    ds = generate(5000, orphan_rate=0.02, in_flight_rate=0.01, now=now)
    cutoff = now - timedelta(hours=PROVISIONING_WINDOW_HOURS)

    # CRM (active, outside provisioning window) vs billing: only active_unbilled is missing.
    crm_active = [(r[0],) for r in ds.crm if r[1] == 'active' and r[3] < cutoff]
    res = _recon(crm_active, [(r[0],) for r in ds.billing])
    assert res.success, res.error
    assert res.output_variables['recon_only_left'] == ds.truth.counts['active_unbilled']
    assert res.output_variables['recon_only_right'] == 0

    # Billing vs HLR: billed_unprovisioned is billed but absent from HLR.
    res = _recon([(r[0],) for r in ds.billing], [(r[0],) for r in ds.hlr])
    assert res.output_variables['recon_only_left'] == ds.truth.counts['billed_unprovisioned']

    # HLR-active vs CRM-active: status_mismatch is on the network but not active in CRM.
    res = _recon([(r[0],) for r in ds.hlr], [(r[0],) for r in ds.crm if r[1] == 'active'])
    assert res.output_variables['recon_only_left'] == ds.truth.counts['status_mismatch']
