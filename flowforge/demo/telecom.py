"""Synthetic telecom dataset with planted revenue-assurance anomalies.

Generates three systems' view of the same subscriber base (CRM, billing and
HLR) with a controllable fraction of planted discrepancies, so demos,
benchmarks and tests do not depend on a partner's data. Everything is derived
from ``seed`` and is fully deterministic. All MSISDNs are fictitious; no real
subscriber data is involved.

Planted categories (ground truth is returned in :class:`GroundTruth`):

``active_unbilled``        CRM active + HLR active, missing from billing (leakage)
``billed_unprovisioned``   billing has the account, HLR has no entry
``status_mismatch``        CRM terminated, HLR still active (free network use)
``in_flight``              CRM activated inside the provisioning window, not yet in
                           HLR/billing: a *correct* state audits must NOT flag
``charge_mismatch``        in all three systems, but billing charge differs from plan price

``activated_at`` is TIMESTAMPTZ, so ``now() - interval`` comparisons do not depend on the
session time zone.

Example reconcile queries over the seeded tables (left = CRM, right = billing)::

    SELECT msisdn FROM demo_crm_subscribers
     WHERE status = 'active' AND activated_at < now() - interval '48 hours'
    SELECT msisdn FROM demo_billing_accounts

Scale: :func:`generate` holds everything in memory (fine to a few hundred thousand
subscribers). :func:`generate_batches` yields bounded batches for multi-million-row seeding
(see ``flowforge/demo/bench.py``); both produce byte-identical data for the same arguments.

CLI::

    python -m flowforge.demo.telecom --dsn postgresql://u:p@host/db --subscribers 100000
    FLOWFORGE_DEMO_ORACLE_PASSWORD=... python -m flowforge.demo.telecom \\
        --oracle-dsn localhost:1521/FREEPDB1 --oracle-user oracle --subscribers 100000
"""
from __future__ import annotations

import argparse
import io
import os
import random
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

PLANS = {'basic': 10.0, 'plus': 25.0, 'max': 60.0}
CATEGORIES = ('active_unbilled', 'billed_unprovisioned', 'status_mismatch', 'charge_mismatch')
PROVISIONING_WINDOW_HOURS = 48
TABLES = ('demo_crm_subscribers', 'demo_billing_accounts', 'demo_hlr_subscribers')

SCHEMA_SQL = """
DROP TABLE IF EXISTS demo_crm_subscribers, demo_billing_accounts, demo_hlr_subscribers;
CREATE TABLE demo_crm_subscribers (
    msisdn VARCHAR(20) PRIMARY KEY, status VARCHAR(20) NOT NULL,
    plan VARCHAR(20) NOT NULL, activated_at TIMESTAMPTZ NOT NULL);
CREATE TABLE demo_billing_accounts (
    msisdn VARCHAR(20) PRIMARY KEY, plan VARCHAR(20) NOT NULL,
    monthly_charge NUMERIC(10,2) NOT NULL);
CREATE TABLE demo_hlr_subscribers (
    msisdn VARCHAR(20) PRIMARY KEY, imsi VARCHAR(20) NOT NULL, state VARCHAR(20) NOT NULL);
"""

# Oracle equivalent. TIMESTAMP WITH TIME ZONE keeps comparisons against SYSTIMESTAMP absolute,
# for the same reason the PostgreSQL column is TIMESTAMPTZ.
ORACLE_SCHEMA_SQL = (
    """CREATE TABLE demo_crm_subscribers (
        msisdn VARCHAR2(20) PRIMARY KEY, status VARCHAR2(20) NOT NULL,
        plan VARCHAR2(20) NOT NULL, activated_at TIMESTAMP WITH TIME ZONE NOT NULL)""",
    """CREATE TABLE demo_billing_accounts (
        msisdn VARCHAR2(20) PRIMARY KEY, plan VARCHAR2(20) NOT NULL,
        monthly_charge NUMBER(10,2) NOT NULL)""",
    """CREATE TABLE demo_hlr_subscribers (
        msisdn VARCHAR2(20) PRIMARY KEY, imsi VARCHAR2(20) NOT NULL, state VARCHAR2(20) NOT NULL)""",
)
_ORACLE_INSERTS = {
    # The offset is part of the string, so the stored instant never depends on the driver's or the
    # session's time zone (binding an aware datetime was observed to be read as session-local time).
    'demo_crm_subscribers': ("INSERT INTO demo_crm_subscribers VALUES (:1, :2, :3, "
                             "TO_TIMESTAMP_TZ(:4, 'YYYY-MM-DD HH24:MI:SS.FF6 TZH:TZM'))"),
    'demo_billing_accounts': 'INSERT INTO demo_billing_accounts VALUES (:1, :2, :3)',
    'demo_hlr_subscribers': 'INSERT INTO demo_hlr_subscribers VALUES (:1, :2, :3)',
}


@dataclass
class GroundTruth:
    """The planted anomalies, as MSISDN lists, for asserting audit output."""
    total: int = 0
    counts: dict[str, int] = field(default_factory=dict)
    keys: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class Dataset:
    crm: list[tuple]       # (msisdn, status, plan, activated_at)
    billing: list[tuple]   # (msisdn, plan, monthly_charge)
    hlr: list[tuple]       # (msisdn, imsi, state)
    truth: GroundTruth


Batch = tuple[list[tuple], list[tuple], list[tuple]]   # (crm rows, billing rows, hlr rows)


def _plan(subscribers: int, orphan_rate: float, in_flight_rate: float, seed: int):
    """Validate, assign each subscriber a role, and derive the ground truth up front.

    The shuffled role list is the only thing shared with row generation; it consumes the RNG
    first, exactly as the original single-pass generator did.
    """
    if subscribers < 1:
        raise ValueError('subscribers must be >= 1')
    if not 0 <= orphan_rate <= 0.2 or not 0 <= in_flight_rate <= 0.2:
        raise ValueError('orphan_rate and in_flight_rate must be between 0 and 0.2')
    rng = random.Random(seed)
    n_each = int(subscribers * orphan_rate)
    n_flight = int(subscribers * in_flight_rate)
    if n_each * len(CATEGORIES) + n_flight > subscribers:
        raise ValueError('requested anomaly rates exceed the subscriber count')

    roles = (['ok'] * (subscribers - n_each * len(CATEGORIES) - n_flight)
             + [c for c in CATEGORIES for _ in range(n_each)] + ['in_flight'] * n_flight)
    rng.shuffle(roles)

    keys: dict[str, list[str]] = {c: [] for c in CATEGORIES + ('in_flight',)}
    for i, role in enumerate(roles):
        if role != 'ok':
            keys[role].append(f'1555{i:07d}')
    truth = GroundTruth(total=subscribers, counts={k: len(v) for k, v in keys.items()}, keys=keys)
    return rng, roles, truth


def _rows_for(i: int, role: str, rng: random.Random, now: datetime):
    """(crm_row, billing_row | None, hlr_row | None) for subscriber ``i``.

    The order and number of RNG draws must not change: it fixes every generated value.
    """
    msisdn = f'1555{i:07d}'
    imsi = f'00101{i:010d}'
    plan = rng.choice(list(PLANS))
    price = PLANS[plan]
    old = now - timedelta(days=rng.randint(10, 900), hours=rng.randint(0, 23))

    if role == 'in_flight':
        recent = now - timedelta(hours=rng.randint(1, PROVISIONING_WINDOW_HOURS - 1))
        return (msisdn, 'active', plan, recent), None, None
    if role == 'status_mismatch':
        return (msisdn, 'terminated', plan, old), None, (msisdn, imsi, 'active')

    hlr = None if role == 'billed_unprovisioned' else (msisdn, imsi, 'active')
    billing = None
    if role != 'active_unbilled':
        charge = price + rng.choice([-5.0, 5.0, 12.5]) if role == 'charge_mismatch' else price
        billing = (msisdn, plan, round(charge, 2))
    return (msisdn, 'active', plan, old), billing, hlr


def _anchor(now: datetime | None) -> datetime:
    return (now or datetime(2026, 1, 1, tzinfo=UTC)).replace(tzinfo=None)


def generate_batches(subscribers: int = 10_000, orphan_rate: float = 0.02,
                     in_flight_rate: float = 0.005, seed: int = 42, now: datetime | None = None,
                     batch_size: int = 100_000) -> tuple[GroundTruth, Iterator[Batch]]:
    """Like :func:`generate`, but returns ``(truth, batches)`` where ``batches`` lazily yields
    ``(crm, billing, hlr)`` row lists of at most ``batch_size`` subscribers each, so peak memory
    stays bounded. The ground truth is known before any row is generated. Consume the iterator
    once; it shares one RNG."""
    if batch_size < 1:
        raise ValueError('batch_size must be >= 1')
    rng, roles, truth = _plan(subscribers, orphan_rate, in_flight_rate, seed)
    anchor = _anchor(now)

    def batches() -> Iterator[Batch]:
        crm: list[tuple] = []
        billing: list[tuple] = []
        hlr: list[tuple] = []
        for i, role in enumerate(roles):
            c, b, h = _rows_for(i, role, rng, anchor)
            crm.append(c)
            if b is not None:
                billing.append(b)
            if h is not None:
                hlr.append(h)
            if (i + 1) % batch_size == 0:
                yield crm, billing, hlr
                crm, billing, hlr = [], [], []
        if crm:
            yield crm, billing, hlr

    return truth, batches()


def generate(subscribers: int = 10_000, orphan_rate: float = 0.02, in_flight_rate: float = 0.005,
             seed: int = 42, now: datetime | None = None) -> Dataset:
    """Build the three tables. ``orphan_rate`` is the fraction of subscribers
    planted per anomaly category (total anomalies ~ 4 x orphan_rate)."""
    truth, batches = generate_batches(subscribers, orphan_rate, in_flight_rate, seed, now,
                                      batch_size=max(1, subscribers))
    crm: list[tuple] = []
    billing: list[tuple] = []
    hlr: list[tuple] = []
    for c, b, h in batches:
        crm += c
        billing += b
        hlr += h
    return Dataset(crm, billing, hlr, truth)


def _copy(cur, table: str, rows: list[tuple]) -> None:
    buf = io.StringIO()
    for r in rows:
        # Dataset timestamps are naive UTC; write an explicit offset so the value is the same
        # instant whatever the session TimeZone is (the column is TIMESTAMPTZ).
        buf.write('\t'.join(
            (v.strftime('%Y-%m-%d %H:%M:%S.%f') + '+00') if isinstance(v, datetime) else str(v)
            for v in r) + '\n')
    buf.seek(0)
    cur.copy_expert(f'COPY {table} FROM STDIN WITH (FORMAT text)', buf)


def seed_postgres_batches(dsn: str, batches: Iterable[Batch]) -> None:
    """Create the ``demo_*`` tables in a PostgreSQL database and load ``batches`` (one transaction).

    Drops and recreates only the three ``demo_*`` tables."""
    import psycopg2
    conn = psycopg2.connect(dsn)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
            for crm, billing, hlr in batches:
                _copy(cur, 'demo_crm_subscribers', crm)
                _copy(cur, 'demo_billing_accounts', billing)
                _copy(cur, 'demo_hlr_subscribers', hlr)
            cur.execute('ANALYZE demo_crm_subscribers; ANALYZE demo_billing_accounts; '
                        'ANALYZE demo_hlr_subscribers')
    finally:
        conn.close()


def seed_postgres(dsn: str, dataset: Dataset) -> None:
    """Create the ``demo_*`` tables in a PostgreSQL database and load the dataset."""
    seed_postgres_batches(dsn, [(dataset.crm, dataset.billing, dataset.hlr)])


def _oracle_rows(table: str, rows: list[tuple]) -> list[tuple]:
    if table != 'demo_crm_subscribers':
        return rows
    # naive-UTC datetimes -> text with an explicit +00:00 offset (see _ORACLE_INSERTS)
    return [(m, s, p, f'{a:%Y-%m-%d %H:%M:%S.%f} +00:00') for m, s, p, a in rows]


def seed_oracle_batches(user: str, password: str, dsn: str, batches: Iterable[Batch]) -> None:
    """Create the ``demo_*`` tables in an Oracle schema and load ``batches``.

    ``dsn`` is ``host:port/service``. Drops and recreates only the three ``demo_*`` tables in the
    connecting user's schema. Uses thin mode (no Oracle Client needed)."""
    import oracledb
    with oracledb.connect(user=user, password=password, dsn=dsn) as conn:
        with conn.cursor() as cur:
            for table in TABLES:
                try:
                    cur.execute(f'DROP TABLE {table} PURGE')
                except oracledb.DatabaseError as e:
                    if 'ORA-00942' not in str(e):      # table does not exist: fine
                        raise
            for ddl in ORACLE_SCHEMA_SQL:
                cur.execute(ddl)
            for crm, billing, hlr in batches:
                for table, rows in (('demo_crm_subscribers', crm), ('demo_billing_accounts', billing),
                                    ('demo_hlr_subscribers', hlr)):
                    if rows:
                        cur.executemany(_ORACLE_INSERTS[table], _oracle_rows(table, rows))
            conn.commit()
            for table in TABLES:
                cur.callproc('DBMS_STATS.GATHER_TABLE_STATS', [user.upper(), table.upper()])


def seed_oracle(user: str, password: str, dsn: str, dataset: Dataset) -> None:
    """Load an in-memory :class:`Dataset` into Oracle (see :func:`seed_oracle_batches`)."""
    seed_oracle_batches(user, password, dsn, [(dataset.crm, dataset.billing, dataset.hlr)])


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description='Seed synthetic telecom demo tables (PostgreSQL and/or Oracle).')
    p.add_argument('--dsn', help='PostgreSQL DSN; demo_* tables are dropped and recreated')
    p.add_argument('--oracle-dsn', help='Oracle host:port/service; demo_* tables are dropped and recreated')
    p.add_argument('--oracle-user', default='oracle')
    p.add_argument('--subscribers', type=int, default=10_000)
    p.add_argument('--orphan-rate', type=float, default=0.02)
    p.add_argument('--in-flight-rate', type=float, default=0.005)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--batch-size', type=int, default=100_000)
    a = p.parse_args(argv)
    if not a.dsn and not a.oracle_dsn:
        p.error('give --dsn (PostgreSQL) and/or --oracle-dsn')
    oracle_password = os.environ.get('FLOWFORGE_DEMO_ORACLE_PASSWORD', '')
    if a.oracle_dsn and not oracle_password:
        p.error('set FLOWFORGE_DEMO_ORACLE_PASSWORD (the password is never taken from the command line)')

    # Anchor timestamps to the current time: audit queries use now() for the provisioning
    # window, so a fixed default date would make the in-flight subscribers look old. Seeding
    # each target needs its own pass over the (deterministic) stream.
    now = datetime.now(UTC)

    def stream():
        return generate_batches(a.subscribers, a.orphan_rate, a.in_flight_rate, a.seed, now, a.batch_size)

    truth = None
    if a.dsn:
        truth, batches = stream()
        seed_postgres_batches(a.dsn, batches)
    if a.oracle_dsn:
        truth, batches = stream()
        seed_oracle_batches(a.oracle_user, oracle_password, a.oracle_dsn, batches)
    print(f'Seeded {a.subscribers} subscribers. Planted: {truth.counts}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
