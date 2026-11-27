"""Volume benchmark for the ``reconcile`` step on PostgreSQL and Oracle.

Seeds the synthetic telecom dataset (``flowforge.demo.telecom``) at one or more sizes, then runs
the orphaned-subscription audit - two ``reconcile`` steps, the same shape as
``examples/telecom-orphaned-subscriptions.yaml`` - through FlowForge's real connection classes in
three layouts:

``pg``      CRM, billing and HLR all in PostgreSQL
``oracle``  all three in Oracle
``cross``   CRM in PostgreSQL, billing and HLR in Oracle (the case the step exists for)

Every run is checked against the planted ground truth, so a fast wrong answer does not count.
Each (layout, size, repeat) runs in its own subprocess, so the reported peak memory belongs to
that run alone.

What this does and does not measure - read before quoting a number:

* It measures the reconcile step end to end (query execution in the source database, streaming
  the rows to Python, diffing, tokenizing the sample). It does not measure pipeline scheduling,
  the API, or the email step.
* Numbers depend entirely on the machine and the database containers' resources. They are
  evidence for *this* setup, not a capacity claim for a production telco system.
* Synthetic data has uniformly distributed, fixed-width keys and no concurrent load; real
  billing tables have skew, wide rows and contention.

Configuration comes from the environment (no secrets on the command line):

    FLOWFORGE_BENCH_PG_DSN            postgresql://user:pass@host:port/database  (a dedicated database)
    FLOWFORGE_BENCH_ORACLE_DSN        host:port/service
    FLOWFORGE_BENCH_ORACLE_USER       default: oracle
    FLOWFORGE_BENCH_ORACLE_PASSWORD

Usage::

    python -m flowforge.demo.bench --sizes 100000,1000000 --repeat 3 --out results.json
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess  # nosec B404 - runs this same module with fixed arguments, no shell
import sys
import time
from datetime import UTC, datetime
from urllib.parse import urlparse

from flowforge.demo.telecom import (
    PROVISIONING_WINDOW_HOURS,
    generate_batches,
    seed_oracle_batches,
    seed_postgres_batches,
)

DEFAULT_ORPHAN_RATE = 0.02
DEFAULT_IN_FLIGHT_RATE = 0.005
DEFAULT_SEED = 42

# system of each table, per layout
LAYOUTS = {
    'pg': {'crm': 'pg', 'billing': 'pg', 'hlr': 'pg'},
    'oracle': {'crm': 'oracle', 'billing': 'oracle', 'hlr': 'oracle'},
    'cross': {'crm': 'pg', 'billing': 'oracle', 'hlr': 'oracle'},
}

# Query templates are static text; the only substitution is the CRM filter below, which is built
# from the constants above (an integer number of hours) and never from user input.
_CRM_VALUES_SQL = ("SELECT msisdn, CASE plan WHEN 'basic' THEN 10 WHEN 'plus' THEN 25 WHEN 'max' THEN 60 END "
                   "FROM demo_crm_subscribers WHERE @CRM_FILTER@")
_CRM_KEYS_SQL = 'SELECT msisdn FROM demo_crm_subscribers WHERE @CRM_FILTER@'
_BILLING_SQL = 'SELECT msisdn, monthly_charge FROM demo_billing_accounts@BILLING_WHERE@'
_HLR_SQL = "SELECT msisdn FROM demo_hlr_subscribers WHERE state = 'active'@HLR_AND@"


def _partition_predicate(dialect: str) -> str:
    """SQL-mode partition filter. The same numeric MSISDN lands in the same partition in both
    databases, which is what lets a cross-system audit split consistently. It is a function of the
    key, so it forces a scan per pass (no index range), a cost the benchmark reports honestly."""
    if dialect == 'oracle':
        return 'MOD(TO_NUMBER(msisdn), {{ partitions }}) = {{ partition_index }}'
    return 'MOD(CAST(msisdn AS BIGINT), {{ partitions }}) = {{ partition_index }}'


def _past_window(dialect: str) -> str:
    h = PROVISIONING_WINDOW_HOURS
    if dialect == 'oracle':
        return f"activated_at < SYSTIMESTAMP - INTERVAL '{h}' HOUR"
    return f"activated_at < now() - interval '{h} hours'"


def audit_queries(dialect_of: dict[str, str], sql_partition: bool = False) -> dict[str, str]:
    """The four audit queries, each written in the dialect of the system it runs in.

    With ``sql_partition`` each also filters on ``{{ partition_index }}`` / ``{{ partitions }}``
    (reconcile's ``partition_mode: sql``)."""
    def pred(system: str) -> str:
        return _partition_predicate(dialect_of[system]) if sql_partition else ''

    crm_filter = "status = 'active' AND " + _past_window(dialect_of['crm'])
    if sql_partition:
        crm_filter += ' AND ' + pred('crm')
    return {
        'crm_values': _CRM_VALUES_SQL.replace('@CRM_FILTER@', crm_filter),
        'crm_keys': _CRM_KEYS_SQL.replace('@CRM_FILTER@', crm_filter),
        'billing': _BILLING_SQL.replace('@BILLING_WHERE@', ' WHERE ' + pred('billing') if sql_partition else ''),
        'hlr': _HLR_SQL.replace('@HLR_AND@', ' AND ' + pred('hlr') if sql_partition else ''),
    }


def expected_counts(counts: dict[str, int]) -> dict[str, dict[str, int]]:
    """What a correct audit must report, from the planted ground-truth counts."""
    return {
        'audit_crm_vs_billing': {'only_left': counts['active_unbilled'], 'only_right': 0,
                                 'mismatched': counts['charge_mismatch']},
        'audit_crm_vs_hlr': {'only_left': counts['billed_unprovisioned'],
                             'only_right': counts['status_mismatch'], 'mismatched': 0},
    }


def peak_rss_mb() -> float:
    """Peak resident memory of this process in MB."""
    if sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes

        class _Counters(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD),
                        ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t),
                        ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                        ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t)]
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        psapi = ctypes.WinDLL('psapi', use_last_error=True)
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE      # a 64-bit handle; the default int truncates it
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(_Counters), wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        c = _Counters()
        c.cb = ctypes.sizeof(c)
        if not psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(c), c.cb):
            raise OSError(ctypes.get_last_error(), 'GetProcessMemoryInfo failed')
        return c.PeakWorkingSetSize / 1024 / 1024
    import resource
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss / 1024 / 1024 if sys.platform == 'darwin' else rss / 1024


# -- configuration ------------------------------------------------------------------------

def _env(name: str, default: str | None = None) -> str:
    v = os.environ.get(name, default)
    if not v:
        raise SystemExit(f'{name} is not set (see the module docstring)')
    return v


def _pg_dsn() -> str:
    return _env('FLOWFORGE_BENCH_PG_DSN')


def _oracle_cfg() -> dict:
    return {'dsn': _env('FLOWFORGE_BENCH_ORACLE_DSN'),
            'user': _env('FLOWFORGE_BENCH_ORACLE_USER', 'oracle'),
            'password': _env('FLOWFORGE_BENCH_ORACLE_PASSWORD')}


def _open_pg():
    from flowforge.connections.postgres import PostgreSQLConnection
    u = urlparse(_pg_dsn())
    return PostgreSQLConnection(host=u.hostname or 'localhost', port=u.port or 5432,
                                database=u.path.lstrip('/'), user=u.username or '', password=u.password or '')


def _open_oracle():
    from flowforge.connections.oracle import OracleConnection
    c = _oracle_cfg()
    host_port, _, service = c['dsn'].partition('/')
    host, _, port = host_port.partition(':')
    return OracleConnection(host=host, port=int(port or 1521), service_name=service,
                            user=c['user'], password=c['password'])


# -- one scenario (runs inside a subprocess) -----------------------------------------------

def run_scenario(layout: str, size: int, orphan_rate: float, in_flight_rate: float, seed: int,
                 partitions: int = 1, partition_mode: str = 'python') -> dict:
    os.environ.setdefault('FLOWFORGE_SECRET_KEY', 'ab' * 32)       # tokenization key for the sample
    from flowforge.steps.reconcile import ReconcileStep

    systems = LAYOUTS[layout]
    q = audit_queries(systems, sql_partition=partitions > 1 and partition_mode == 'sql')
    openers = {'pg': _open_pg, 'oracle': _open_oracle}
    truth, _ = generate_batches(size, orphan_rate, in_flight_rate, seed)

    class _Bench(ReconcileStep):
        def _open(self, conn_id):                       # 'L:pg' / 'R:oracle'
            return openers[conn_id.split(':')[1]]()

    steps = [
        ('audit_crm_vs_billing', 'crm', q['crm_values'], 'billing', q['billing'], 'values', 'billing'),
        ('audit_crm_vs_hlr', 'crm', q['crm_keys'], 'hlr', q['hlr'], 'keys', 'hlr'),
    ]
    want = expected_counts(truth.counts)
    out_steps = {}
    total = 0.0
    for name, lt, lq, rt, rq, compare, prefix in steps:
        cfg = {'left_connection_id': f'L:{systems[lt]}', 'right_connection_id': f'R:{systems[rt]}',
               'left_query': lq, 'right_query': rq, 'compare': compare, 'tolerance': 0.005,
               'sample_size': 20, 'tokenize_keys': True, 'output_prefix': prefix,
               'partitions': partitions, 'partition_mode': partition_mode,
               'max_rows': max(5_000_000, size * 2)}
        t0 = time.perf_counter()
        r = _Bench(name, cfg).run({'steps': {}})
        dt = time.perf_counter() - t0
        total += dt
        if not r.success:
            out_steps[name] = {'seconds': round(dt, 3), 'success': False, 'error': r.error}
            continue
        v = r.output_variables
        got = {'only_left': v[f'{prefix}_only_left'], 'only_right': v[f'{prefix}_only_right'],
               'mismatched': v[f'{prefix}_mismatched']}
        out_steps[name] = {
            'seconds': round(dt, 3), 'success': True,
            'left_rows': v[f'{prefix}_left_count'], 'right_rows': v[f'{prefix}_right_count'],
            'rows_per_second': round((v[f'{prefix}_left_count'] + v[f'{prefix}_right_count']) / dt),
            'found': got, 'expected': want[name], 'correct': got == want[name],
        }
    return {'layout': layout, 'size': size, 'partitions': partitions, 'partition_mode': partition_mode,
            'total_seconds': round(total, 3),
            'peak_rss_mb': round(peak_rss_mb(), 1), 'steps': out_steps,
            'correct': all(s.get('correct') for s in out_steps.values())}


# -- orchestration ------------------------------------------------------------------------

def _server_info() -> dict:
    info: dict = {'platform': platform.platform(), 'python': platform.python_version(),
                  'cpu_count': os.cpu_count()}
    try:
        import psycopg2
        with psycopg2.connect(_pg_dsn()) as c, c.cursor() as cur:
            cur.execute('select version()')
            info['postgresql'] = cur.fetchone()[0].split(' on ')[0]
    except Exception as e:  # informational only
        info['postgresql'] = f'unavailable ({type(e).__name__})'
    try:
        import oracledb
        o = _oracle_cfg()
        with oracledb.connect(user=o['user'], password=o['password'], dsn=o['dsn']) as c, c.cursor() as cur:
            cur.execute('select banner_full from v$version fetch first 1 rows only')
            info['oracle'] = cur.fetchone()[0].split('\n')[0]
    except Exception as e:
        info['oracle'] = f'unavailable ({type(e).__name__})'
    return info


def seed_all(size: int, orphan_rate: float, in_flight_rate: float, seed: int) -> dict:
    now = datetime.now(UTC)        # the window is evaluated against now(): seed fresh for every size
    o = _oracle_cfg()
    timings = {}
    t0 = time.perf_counter()
    _, batches = generate_batches(size, orphan_rate, in_flight_rate, seed, now)
    seed_postgres_batches(_pg_dsn(), batches)
    timings['seed_pg_seconds'] = round(time.perf_counter() - t0, 1)
    t0 = time.perf_counter()
    _, batches = generate_batches(size, orphan_rate, in_flight_rate, seed, now)
    seed_oracle_batches(o['user'], o['password'], o['dsn'], batches)
    timings['seed_oracle_seconds'] = round(time.perf_counter() - t0, 1)
    return timings


def _run_child(layout: str, size: int, orphan_rate: float, in_flight_rate: float, seed: int,
               partitions: int = 1, partition_mode: str = 'python') -> dict:
    cmd = [sys.executable, '-I', '-m', 'flowforge.demo.bench', 'scenario', '--layout', layout,
           '--size', str(size), '--orphan-rate', str(orphan_rate),
           '--in-flight-rate', str(in_flight_rate), '--seed', str(seed),
           '--partitions', str(partitions), '--partition-mode', partition_mode]
    p = subprocess.run(cmd, capture_output=True, text=True, env=os.environ.copy(), check=False)  # nosec B603 - fixed argv list, no shell, sys.executable only
    if p.returncode != 0:
        return {'layout': layout, 'size': size, 'partitions': partitions, 'partition_mode': partition_mode,
                'error': (p.stderr or p.stdout)[-800:], 'correct': False}
    return json.loads(p.stdout.strip().splitlines()[-1])


def parse_variants(text: str) -> list[tuple[int, str]]:
    """``'1:python,4:sql'`` -> ``[(1, 'python'), (4, 'sql')]``; a bare ``'4'`` means python mode."""
    out = []
    for item in (x.strip() for x in text.split(',') if x.strip()):
        n, _, mode = item.partition(':')
        mode = mode or 'python'
        if not n.isdigit() or int(n) < 1 or mode not in ('python', 'sql'):
            raise ValueError(f'bad variant {item!r}: expected N or N:python or N:sql with N >= 1')
        out.append((int(n), mode))
    return out


def summarize(runs: list[dict]) -> list[dict]:
    """Group repeated runs of one (size, layout, partitions, mode) into best/median/worst."""
    groups: dict[tuple, list[dict]] = {}
    for r in runs:
        key = (r['size'], r['layout'], r.get('partitions', 1), r.get('partition_mode', 'python'))
        groups.setdefault(key, []).append(r)
    rows = []
    for (size, layout, partitions, mode), rs in sorted(groups.items()):
        ok = [r for r in rs if r.get('correct')]
        times = [r['total_seconds'] for r in ok]
        rows.append({
            'size': size, 'layout': layout, 'partitions': partitions, 'partition_mode': mode,
            'runs': len(rs), 'correct_runs': len(ok),
            'best_s': min(times) if times else None,
            'median_s': round(statistics.median(times), 2) if times else None,
            'worst_s': max(times) if times else None,
            'peak_rss_mb': max((r['peak_rss_mb'] for r in ok), default=None),
        })
    return rows


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = p.add_subparsers(dest='cmd')
    s = sub.add_parser('scenario', help='(internal) run one layout/size and print JSON')
    s.add_argument('--layout', choices=sorted(LAYOUTS), required=True)
    s.add_argument('--size', type=int, required=True)
    s.add_argument('--partitions', type=int, default=1)
    s.add_argument('--partition-mode', choices=['python', 'sql'], default='python')
    for sp in (s, p):
        sp.add_argument('--orphan-rate', type=float, default=DEFAULT_ORPHAN_RATE)
        sp.add_argument('--in-flight-rate', type=float, default=DEFAULT_IN_FLIGHT_RATE)
        sp.add_argument('--seed', type=int, default=DEFAULT_SEED)
    p.add_argument('--sizes', default='100000,1000000', help='comma-separated subscriber counts')
    p.add_argument('--layouts', default=','.join(LAYOUTS))
    p.add_argument('--variants', default='1:python',
                   help="reconcile partitioning to measure, e.g. '1:python,4:python,4:sql' (N passes : mode)")
    p.add_argument('--repeat', type=int, default=3)
    p.add_argument('--out', default='benchmark-results.json')
    a = p.parse_args(argv)

    if a.cmd == 'scenario':
        print(json.dumps(run_scenario(a.layout, a.size, a.orphan_rate, a.in_flight_rate, a.seed,
                                      a.partitions, a.partition_mode)))
        return 0

    layouts = [x for x in a.layouts.split(',') if x]
    bad = [x for x in layouts if x not in LAYOUTS]
    if bad:
        p.error(f'unknown layout(s): {bad}')
    try:
        variants = parse_variants(a.variants)
    except ValueError as e:
        p.error(str(e))
    result: dict = {'started': datetime.now(UTC).isoformat(timespec='seconds'), 'environment': _server_info(),
                    'orphan_rate': a.orphan_rate, 'in_flight_rate': a.in_flight_rate, 'seed': a.seed,
                    'seeding': {}, 'runs': []}
    for size in (int(x) for x in a.sizes.split(',') if x):
        print(f'== {size:,} subscribers: seeding ...', flush=True)
        result['seeding'][str(size)] = seed_all(size, a.orphan_rate, a.in_flight_rate, a.seed)
        print(f'   {result["seeding"][str(size)]}', flush=True)
        for partitions, mode in variants:
            for layout in layouts:
                for i in range(a.repeat):
                    r = _run_child(layout, size, a.orphan_rate, a.in_flight_rate, a.seed, partitions, mode)
                    result['runs'].append(r)
                    label = f'{layout:6} {partitions}x{mode:6}'
                    print(f'   {label} run {i + 1}: ' + (f'{r["total_seconds"]}s, peak {r["peak_rss_mb"]} MB, '
                          f'correct={r["correct"]}' if 'error' not in r else f'ERROR {r["error"][:200]}'),
                          flush=True)
    result['summary'] = summarize(result['runs'])
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    print(f'wrote {a.out}')
    return 0 if all(r.get('correct') for r in result['runs']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
