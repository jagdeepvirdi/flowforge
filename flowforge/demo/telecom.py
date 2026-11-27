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

Example reconcile queries over the seeded tables (left = CRM, right = billing)::

    SELECT msisdn FROM demo_crm_subscribers
     WHERE status = 'active' AND activated_at < now() - interval '48 hours'
    SELECT msisdn FROM demo_billing_accounts

CLI::

    python -m flowforge.demo.telecom --dsn postgresql://u:p@host/db --subscribers 100000
"""
from __future__ import annotations

import argparse
import io
import random
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

PLANS = {'basic': 10.0, 'plus': 25.0, 'max': 60.0}
CATEGORIES = ('active_unbilled', 'billed_unprovisioned', 'status_mismatch', 'charge_mismatch')
PROVISIONING_WINDOW_HOURS = 48

SCHEMA_SQL = """
DROP TABLE IF EXISTS demo_crm_subscribers, demo_billing_accounts, demo_hlr_subscribers;
CREATE TABLE demo_crm_subscribers (
    msisdn VARCHAR(20) PRIMARY KEY, status VARCHAR(20) NOT NULL,
    plan VARCHAR(20) NOT NULL, activated_at TIMESTAMP NOT NULL);
CREATE TABLE demo_billing_accounts (
    msisdn VARCHAR(20) PRIMARY KEY, plan VARCHAR(20) NOT NULL,
    monthly_charge NUMERIC(10,2) NOT NULL);
CREATE TABLE demo_hlr_subscribers (
    msisdn VARCHAR(20) PRIMARY KEY, imsi VARCHAR(20) NOT NULL, state VARCHAR(20) NOT NULL);
"""


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


def generate(subscribers: int = 10_000, orphan_rate: float = 0.02, in_flight_rate: float = 0.005,
             seed: int = 42, now: datetime | None = None) -> Dataset:
    """Build the three tables. ``orphan_rate`` is the fraction of subscribers
    planted per anomaly category (total anomalies ~ 4 x orphan_rate)."""
    if subscribers < 1:
        raise ValueError('subscribers must be >= 1')
    if not 0 <= orphan_rate <= 0.2 or not 0 <= in_flight_rate <= 0.2:
        raise ValueError('orphan_rate and in_flight_rate must be between 0 and 0.2')
    rng = random.Random(seed)
    now = (now or datetime(2026, 1, 1, tzinfo=UTC)).replace(tzinfo=None)

    n_each = int(subscribers * orphan_rate)
    n_flight = int(subscribers * in_flight_rate)
    if n_each * len(CATEGORIES) + n_flight > subscribers:
        raise ValueError('requested anomaly rates exceed the subscriber count')

    roles = (['ok'] * (subscribers - n_each * len(CATEGORIES) - n_flight)
             + [c for c in CATEGORIES for _ in range(n_each)] + ['in_flight'] * n_flight)
    rng.shuffle(roles)

    crm, billing, hlr = [], [], []
    keys: dict[str, list[str]] = {c: [] for c in CATEGORIES + ('in_flight',)}
    for i, role in enumerate(roles):
        msisdn = f'1555{i:07d}'
        imsi = f'00101{i:010d}'
        plan = rng.choice(list(PLANS))
        price = PLANS[plan]
        old = now - timedelta(days=rng.randint(10, 900), hours=rng.randint(0, 23))

        if role == 'in_flight':
            recent = now - timedelta(hours=rng.randint(1, PROVISIONING_WINDOW_HOURS - 1))
            crm.append((msisdn, 'active', plan, recent))
            keys[role].append(msisdn)
            continue
        if role == 'status_mismatch':
            crm.append((msisdn, 'terminated', plan, old))
            hlr.append((msisdn, imsi, 'active'))
            keys[role].append(msisdn)
            continue

        crm.append((msisdn, 'active', plan, old))
        if role != 'billed_unprovisioned':
            hlr.append((msisdn, imsi, 'active'))
        if role != 'active_unbilled':
            charge = price + rng.choice([-5.0, 5.0, 12.5]) if role == 'charge_mismatch' else price
            billing.append((msisdn, plan, round(charge, 2)))
        if role != 'ok':
            keys[role].append(msisdn)

    truth = GroundTruth(total=subscribers, counts={k: len(v) for k, v in keys.items()}, keys=keys)
    return Dataset(crm, billing, hlr, truth)


def _copy(cur, table: str, rows: list[tuple]) -> None:
    buf = io.StringIO()
    for r in rows:
        buf.write('\t'.join(str(v) for v in r) + '\n')
    buf.seek(0)
    cur.copy_expert(f'COPY {table} FROM STDIN WITH (FORMAT text)', buf)


def seed_postgres(dsn: str, dataset: Dataset) -> None:
    """Create the ``demo_*`` tables in a PostgreSQL database and load the dataset.

    Drops and recreates only the three ``demo_*`` tables."""
    import psycopg2
    conn = psycopg2.connect(dsn)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
            _copy(cur, 'demo_crm_subscribers', dataset.crm)
            _copy(cur, 'demo_billing_accounts', dataset.billing)
            _copy(cur, 'demo_hlr_subscribers', dataset.hlr)
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description='Seed synthetic telecom demo tables (PostgreSQL).')
    p.add_argument('--dsn', required=True, help='PostgreSQL DSN; demo_* tables are dropped and recreated')
    p.add_argument('--subscribers', type=int, default=10_000)
    p.add_argument('--orphan-rate', type=float, default=0.02)
    p.add_argument('--in-flight-rate', type=float, default=0.005)
    p.add_argument('--seed', type=int, default=42)
    a = p.parse_args(argv)
    # Anchor timestamps to the current time: audit queries use now() for the provisioning
    # window, so a fixed default date would make the in-flight subscribers look old.
    ds = generate(a.subscribers, a.orphan_rate, a.in_flight_rate, a.seed, now=datetime.now(UTC))
    seed_postgres(a.dsn, ds)
    print(f'Seeded {a.subscribers} subscribers. Planted: {ds.truth.counts}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
