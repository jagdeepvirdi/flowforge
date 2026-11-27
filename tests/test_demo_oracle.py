"""Oracle seeding of the synthetic dataset (live; skipped unless Oracle credentials are in the env).

Needs FLOWFORGE_BENCH_ORACLE_DSN (host:port/service) and FLOWFORGE_BENCH_ORACLE_PASSWORD, with
FLOWFORGE_BENCH_ORACLE_USER defaulting to ``oracle``. It drops and recreates only the three
``demo_*`` tables in that user's schema.
"""
import os
from datetime import UTC, datetime

import pytest

from flowforge.demo.telecom import (
    _oracle_rows,
    generate,
    generate_batches,
    seed_oracle,
    seed_oracle_batches,
)

oracledb = pytest.importorskip('oracledb')


def test_oracle_timestamps_carry_an_explicit_utc_offset():
    rows = _oracle_rows('demo_crm_subscribers', [('1', 'active', 'basic', datetime(2026, 1, 2, 3, 4, 5, 678))])
    assert rows == [('1', 'active', 'basic', '2026-01-02 03:04:05.000678 +00:00')]
    other = [('1', 'a', 'b')]
    assert _oracle_rows('demo_billing_accounts', other) is other       # only the CRM table has a timestamp


@pytest.fixture(scope='module')
def oracle():
    dsn = os.environ.get('FLOWFORGE_BENCH_ORACLE_DSN')
    password = os.environ.get('FLOWFORGE_BENCH_ORACLE_PASSWORD')
    if not dsn or not password:
        pytest.skip('set FLOWFORGE_BENCH_ORACLE_DSN and FLOWFORGE_BENCH_ORACLE_PASSWORD to run the Oracle tests')
    user = os.environ.get('FLOWFORGE_BENCH_ORACLE_USER', 'oracle')
    try:
        ds = generate(3000, orphan_rate=0.02, in_flight_rate=0.01, seed=21, now=datetime.now(UTC))
        seed_oracle(user, password, dsn, ds)
    except oracledb.Error as e:
        pytest.skip(f'Oracle not available: {e}')
    return user, password, dsn, ds


def _query(oracle, sql, tz=None):
    user, password, dsn, _ = oracle
    with oracledb.connect(user=user, password=password, dsn=dsn) as conn, conn.cursor() as cur:
        if tz:
            cur.execute(f"alter session set time_zone = '{tz}'")
        cur.execute(sql)
        return cur.fetchall()


def test_row_counts_match_the_dataset(oracle):
    ds = oracle[3]
    assert _query(oracle, 'select count(*) from demo_crm_subscribers')[0][0] == len(ds.crm)
    assert _query(oracle, 'select count(*) from demo_billing_accounts')[0][0] == len(ds.billing)
    assert _query(oracle, 'select count(*) from demo_hlr_subscribers')[0][0] == len(ds.hlr)


def test_every_stored_instant_equals_the_generated_one(oracle):
    """python-oracledb discards the tzinfo of an aware datetime and stores the wall clock with the
    *session's* offset, shifting every timestamp by the client's UTC offset. Compare each stored
    instant (as UTC) with the generator's value: exact, and independent of which rows sit near the
    48 h window edge (a count-based check passed by luck of the seed)."""
    ds = oracle[3]
    stored = dict(_query(oracle, "select msisdn, to_char(sys_extract_utc(activated_at), "
                                 "'YYYY-MM-DD HH24:MI:SS.FF6') from demo_crm_subscribers"))
    expected = {r[0]: f'{r[3]:%Y-%m-%d %H:%M:%S.%f}' for r in ds.crm}
    assert stored == expected


@pytest.mark.parametrize('tz', ['UTC', '+05:30', '+14:00', '-11:00'])
def test_in_flight_window_does_not_depend_on_the_session_time_zone(oracle, tz):
    """Query side: the 48 h window counts the planted in-flight rows whatever the session zone."""
    ds = oracle[3]
    recent = _query(oracle, "select count(*) from demo_crm_subscribers "
                            "where activated_at > systimestamp - interval '48' hour", tz)[0][0]
    assert recent == ds.truth.counts['in_flight']


def test_streaming_seed_matches_in_memory_seed(oracle):
    user, password, dsn, ds = oracle
    truth, batches = generate_batches(3000, 0.02, 0.01, seed=21, now=datetime.now(UTC), batch_size=700)
    seed_oracle_batches(user, password, dsn, batches)
    assert _query(oracle, 'select count(*) from demo_crm_subscribers')[0][0] == len(ds.crm)
    assert _query(oracle, 'select count(*) from demo_billing_accounts')[0][0] == len(ds.billing)
    assert truth.counts == ds.truth.counts
