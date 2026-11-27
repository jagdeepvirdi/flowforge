# Reconcile volume benchmark

Measured 2026-11-27. Raw data: [`benchmarks/reconcile-2026-11-27.json`](benchmarks/reconcile-2026-11-27.json).
Harness: `flowforge/demo/bench.py`. Dataset: `flowforge/demo/telecom.py` (synthetic, planted anomalies).

**Read this first.** These numbers describe one laptop running default-configured Docker
containers against synthetic data. They show how the `reconcile` step behaves and scales on that
setup. They are **not** a capacity claim for a production telecom system, and they do not support
the words "extreme volume" or "carrier grade". The largest table here has 5 million subscribers;
a large operator's billing and mediation tables are one to two orders of magnitude bigger.

## What was run

The orphaned-subscription audit (two `reconcile` steps, the same shape as
`examples/telecom-orphaned-subscriptions.yaml`) through FlowForge's real `PostgreSQLConnection`
and `OracleConnection` classes:

1. **CRM vs billing**, comparing a value (charge against plan price) with a 0.005 tolerance. Finds
   active-but-unbilled subscribers and charge mismatches.
2. **CRM vs HLR**, comparing keys. Finds provisioning gaps and network access without an active
   CRM record.

Sample keys are tokenized (`tokenize_keys: true`), as in the shipped template. Three layouts:

| Layout | CRM | Billing | HLR |
|---|---|---|---|
| `pg` | PostgreSQL | PostgreSQL | PostgreSQL |
| `oracle` | Oracle | Oracle | Oracle |
| `cross` | PostgreSQL | Oracle | Oracle |

`cross` is the case the step exists for: no single query can join those systems.

Every run was checked against the planted ground truth (2% of subscribers per anomaly category, 0.5%
in-flight subscribers that must *not* be flagged). A run that is fast but wrong does not count; all
24 runs below were correct, with exactly the planted counts and no false positives.

## Results

Wall-clock time for both steps together, over 3 runs (1M and below) or 2 runs (5M). Peak memory
is the benchmark process's peak working set.

| Subscribers | Layout | Best | Median | Worst | Peak memory |
|---:|---|---:|---:|---:|---:|
| 100,000 | pg | 1.04 s | 1.08 s | 1.13 s | 71 MB |
| 100,000 | oracle | 1.29 s | 1.30 s | 1.33 s | 71 MB |
| 100,000 | cross | 1.29 s | 1.36 s | 1.37 s | 83 MB |
| 1,000,000 | pg | 8.5 s | 8.6 s | 8.8 s | 244 MB |
| 1,000,000 | oracle | 10.9 s | 11.0 s | 11.0 s | 244 MB |
| 1,000,000 | cross | 9.5 s | 9.7 s | 10.0 s | 255 MB |
| 5,000,000 | pg | 46.0 s | 46.9 s | 47.8 s | 960 MB |
| 5,000,000 | oracle | 56.0 s | 56.3 s | 56.5 s | 960 MB |
| 5,000,000 | cross | 48.2 s | 48.4 s | 48.5 s | 972 MB |

At 5M subscribers each step reads about 4.8 million rows per side (about 9.7 million rows for the
CRM-vs-HLR step). Throughput was **roughly 300,000 to 575,000 rows per second** end to end,
depending on the step and database, and held steady from 1M to 5M.

### What the numbers say

- **Time scales close to linearly**: 5x the subscribers took about 5.4x as long (PostgreSQL, 1M to
  5M).
- **Memory scales linearly, at about 180 bytes per distinct key on the left side.** The left side
  is held in memory as a dictionary; the right side is streamed. This is the step's binding
  constraint, not time.
- **Oracle was about 20-30% slower than PostgreSQL** on the same data here (20% at 100k and 5M, 28% at 1M), and the cross-system
  layout fell between them. I did not profile why, so I make no claim about the cause (driver,
  database, container limits, or query plans could each contribute). Oracle here is the Free
  edition in a container, which is resource-limited; a production Oracle server will differ.
- **Tokenizing the sample should be negligible**: it touches at most 20 keys per category. I did not
  time a run with it off, so this is by construction, not measured.

## Bounded memory: partitioned passes

`partitions: N` (see `docs/step-types.md`) runs the comparison as N passes over disjoint key subsets.
Measured on 5,000,000 subscribers, one run per cell (same machine and setup as above, seeded fresh for
this run), raw data in [`benchmarks/reconcile-partitions-2026-11-27.json`](benchmarks/reconcile-partitions-2026-11-27.json).
Every run was correct against the planted ground truth.

| Layout | Passes | Mode | Time | vs 1 pass | Peak memory | vs 1 pass |
|---|---:|---|---:|---:|---:|---:|
| pg | 1 | - | 44.9 s | - | 959 MB | - |
| pg | 4 | python | 135.8 s | 3.0x | 328 MB | -66% |
| pg | 4 | sql | 52.3 s | 1.16x | 328 MB | -66% |
| pg | 8 | sql | 63.1 s | 1.41x | 223 MB | -77% |
| cross | 1 | - | 48.8 s | - | 972 MB | - |
| cross | 4 | python | 159.7 s | 3.3x | 341 MB | -65% |
| cross | 4 | sql | 68.9 s | 1.41x | 340 MB | -65% |
| cross | 8 | sql | 79.4 s | 1.63x | 236 MB | -76% |

- **Memory falls roughly as 1/N**, down to a floor of about 70 MB for the process itself. It is a little
  above the ideal `(959 - 71)/N + 71` because partitions are not perfectly even.
- **Python mode buys memory with time**: each pass re-reads both full result sets, so 4 passes cost about 3x.
  Its advantage is that it works across any databases with no SQL changes.
- **SQL mode costs far less time but is not free**: +16% to +63% here. The predicate
  (`MOD(CAST(msisdn AS BIGINT), N) = k`, `TO_NUMBER` on Oracle) is a function of the key, so it cannot
  use an index range and each pass scans the table again; that cost grows with N. A predicate the
  database can use an index for (a key range) would likely be cheaper, but ranges are only balanced if
  the keys are spread evenly, which synthetic data is and real numbering plans often are not. Not tested.
- **The SQL predicate must pick the same keys on both sides.** The step cannot check that. A mismatch
  gives wrong counts, not an error; the step only refuses queries that never mention `partition_index`.
- **One run per cell**, so no spread is shown. The earlier tables use 2-3 runs and were within a few
  percent of each other, but these cells could vary more than that.
- **Not tested**: more than 8 passes, the Oracle-only layout, sizes above 5M, a left side larger than
  RAM even when partitioned (each pass still holds its whole partition), or the unpartitioned
  default `max_rows` cap of 5M (this run raised `max_rows`; with partitions the cap applies per pass).

## What this does not tell you

- **Not production scale.** Largest size 5M subscribers. Nothing above that was run.
- **Synthetic data**: uniform, fixed-width keys; no skew, no wide rows, no NULLs or duplicate keys
  beyond what the generator makes. Real billing tables behave differently.
- **No concurrency.** One audit at a time on an otherwise idle machine. Real source databases are
  busy; scans compete with production load.
- **Local, default-configured containers** on one machine (Windows 11, 16 logical CPUs, 15.3 GiB
  visible to Docker). No network between FlowForge and the databases beyond loopback, which flatters
  the cross-system layout. A real deployment adds network latency and throughput limits.
- **Time was not split** between database execution, transfer to Python and the diff, so I cannot
  say which dominates, or how much faster the databases could be with tuning or better indexes.
- **Only the reconcile step** was measured, not scheduling, the API, email, or run-history writes.

## Extrapolation (not measured)

If memory stays at about 180 bytes per key and time stays linear, a **50 million**-subscriber side
would need roughly **9 GB** of RAM and on the order of **8-10 minutes** for this audit. Treat that as
an estimate to be tested, not a result. More importantly, the step's default `max_rows` of
5,000,000 distinct keys per side would stop it first: it fails with a clear message instead of
exhausting memory. For tables beyond a few tens of millions of keys the current design needs
either a narrower left side (filter or aggregate in SQL) or partitioned passes. **Partitioned passes
are now built and measured up to 5M** (section above): with 8 SQL-mode passes a 50M-key side would be
projected at roughly 1 GB per pass instead of 9 GB, but that is an extrapolation of a 77% reduction
measured at 5M, and the extra table scans per pass at that size were not measured. Other options, not
built:

- **Streamed merge**: `ORDER BY key` on both sides and merge-join without holding either side. Needs a
  sort in each source database and consistent collation across systems.
- **Push the set difference into SQL** where both systems can see each other (database link or
  external table), keeping FlowForge out of the data path.

## Reproduce

Create a dedicated database for PostgreSQL (do **not** point it at FlowForge's own database; the
internal-database guard refuses that), then:

```bash
export FLOWFORGE_BENCH_PG_DSN='postgresql://USER:PASSWORD@HOST:PORT/DATABASE'
export FLOWFORGE_BENCH_ORACLE_DSN='HOST:1521/SERVICE'
export FLOWFORGE_BENCH_ORACLE_USER='USER'
export FLOWFORGE_BENCH_ORACLE_PASSWORD='PASSWORD'
python -m flowforge.demo.bench --sizes 100000,1000000,5000000 --repeat 3 --out results.json
```

The harness drops and recreates only the three `demo_*` tables in each database. Seeding 5M
subscribers took about 2 minutes per database here. Credentials come from the environment, never
from the command line.
