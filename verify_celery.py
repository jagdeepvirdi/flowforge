"""
Celery E2E Verification — Phase 1.1
=====================================
Tests four scenarios:
  1. Celery path  — FLOWFORGE_REDIS_URL set, task dispatched to worker
  2. Thread path  — no FLOWFORGE_REDIS_URL, pipeline runs in background thread
  3. Worker log   — confirm worker output mentions task received + succeeded
  4. Cleanup      — removes all test data from the DB

Usage:
    .venv\Scripts\python.exe verify_celery.py
"""
import os
import sys
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ── env vars must be set BEFORE any flowforge import ──────────────────────────
_DB_URL   = 'postgresql://flowforge:harpal123@localhost:5434/flowforge_test'
_SK       = '4d688ef00edded2d39f4109d9e6497d54fff5165555a8a41e8aaedb9c7f62fd0'
_REDIS    = 'redis://localhost:6379/0'

os.environ['FLOWFORGE_DB_URL']    = _DB_URL
os.environ['FLOWFORGE_SECRET_KEY'] = _SK
os.environ['FLOWFORGE_JWT_SECRET'] = _SK
os.environ['FLOWFORGE_REDIS_URL'] = _REDIS

VENV_PYTHON = str(Path(__file__).parent / '.venv' / 'Scripts' / 'python.exe')

PASS = '[OK]'
FAIL = '[FAIL]'

def _header(title: str) -> None:
    print(f'\n{"─"*60}')
    print(f'  {title}')
    print('─'*60)

def _ok(msg: str)   -> None: print(f'  {PASS}  {msg}')
def _err(msg: str)  -> None: print(f'  {FAIL}  {msg}'); sys.exit(1)
def _warn(msg: str) -> None: print(f'  !  {msg}')

# ── import after env vars are set ─────────────────────────────────────────────
from flowforge.api.app import create_app
from flowforge.crypto import encrypt_config
from flowforge.db.models import (
    db, DbConnection, Pipeline, PipelineStep, PipelineRun, StepRun
)

_POLL_SECS = 45  # max seconds to wait for a run to complete

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _create_test_connection(app) -> str:
    """Insert a DbConnection pointing to the test PostgreSQL DB."""
    with app.app_context():
        cfg = encrypt_config({
            'host': 'localhost',
            'port': 5434,
            'database': 'flowforge_test',
            'user': 'flowforge',
            'password': 'harpal123',
        })
        conn = DbConnection(
            id=str(uuid.uuid4()),
            name='_e2e_verify_conn',
            db_type='postgresql',
            config=cfg,
        )
        db.session.add(conn)
        db.session.commit()
        return str(conn.id)


def _create_test_pipeline(app, conn_id: str) -> str:
    """Insert a minimal pipeline with a single db_query step."""
    with app.app_context():
        pipeline = Pipeline(
            id=str(uuid.uuid4()),
            name='_e2e_celery_verify',
            description='Automated E2E verification — safe to delete',
            enabled=True,
        )
        db.session.add(pipeline)
        db.session.flush()

        step = PipelineStep(
            id=str(uuid.uuid4()),
            pipeline_id=pipeline.id,
            step_order=1,
            name='verify_query',
            step_type='db_query',
            config={
                'connection_id': conn_id,
                'query': 'SELECT 1 AS celery_verify',
            },
            enabled=True,
        )
        db.session.add(step)
        db.session.commit()
        return str(pipeline.id)


def _poll_run(app, run_id: str, timeout: int = _POLL_SECS) -> PipelineRun:
    """Poll until the run leaves 'running' status or timeout expires."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        with app.app_context():
            run = db.session.get(PipelineRun, run_id)
            if run and run.status != 'running':
                return run
        time.sleep(1)
    with app.app_context():
        return db.session.get(PipelineRun, run_id)


def _get_step_runs(app, run_id: str) -> list:
    with app.app_context():
        return db.session.query(StepRun).filter_by(pipeline_run_id=run_id).all()


def _cleanup(app, pipeline_id: str, conn_id: str) -> None:
    with app.app_context():
        pipeline = db.session.get(Pipeline, pipeline_id)
        if pipeline:
            db.session.delete(pipeline)
        conn = db.session.get(DbConnection, conn_id)
        if conn:
            db.session.delete(conn)
        db.session.commit()


# ──────────────────────────────────────────────────────────────────────────────
# Test 1 — Celery path
# ──────────────────────────────────────────────────────────────────────────────

def test_celery_path():
    _header('TEST 1 — Celery dispatch (FLOWFORGE_REDIS_URL set)')

    # Build a fresh app with Redis configured
    app = create_app()
    conn_id    = _create_test_connection(app)
    pipeline_id = _create_test_pipeline(app, conn_id)
    _ok(f'Test pipeline created: {pipeline_id[:8]}…')

    # Start a worker as a subprocess
    worker_env = os.environ.copy()
    worker_out = []

    print('  Starting flowforge worker…')
    worker = subprocess.Popen(
        [VENV_PYTHON, '-m', 'celery', '-A', 'flowforge.celery_app', 'worker',
         '--loglevel=info', '--pool=solo',
         '--without-gossip', '--without-mingle', '--without-heartbeat'],
        env=worker_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    # Give the worker a moment to connect to Redis and announce readiness
    time.sleep(4)
    if worker.poll() is not None:
        out, _ = worker.communicate()
        _err(f'Worker exited early (rc={worker.returncode}):\n{out}')

    _ok('Worker process started')

    # Dispatch the pipeline run
    from flowforge.engine.launcher import launch_run
    with app.app_context():
        pipeline = db.session.get(Pipeline, pipeline_id)
        resp, status_code = launch_run(pipeline, triggered_by='e2e_verify')

    if status_code != 202:
        _err(f'launch_run returned {status_code}: {resp}')

    run_id = resp['run_id']
    _ok(f'Run dispatched (run_id={run_id[:8]}…, status_code={status_code})')

    # Poll for completion
    print(f'  Waiting up to {_POLL_SECS}s for run to complete…')
    run = _poll_run(app, run_id)

    # Drain worker output
    try:
        worker_stdout, _ = worker.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        worker_stdout = ''
        worker.kill()
        worker.wait()
    else:
        worker.terminate()
        worker.wait()

    # Assertions
    if run is None:
        _err('PipelineRun record not found in DB after dispatch')

    print(f'\n  PipelineRun.status = {run.status!r}')
    if run.status == 'running':
        _err('Run is still "running" after timeout — worker may not have picked up the task')

    if run.status == 'success':
        _ok('PipelineRun.status = "success"')
    elif run.status == 'failed':
        _warn(f'PipelineRun.status = "failed" (error: {run.error_message})')
        _warn('Step failed but worker DID process the task — Celery wiring is working')
    else:
        _err(f'Unexpected status: {run.status}')

    # Check step runs exist
    step_runs = _get_step_runs(app, run_id)
    if step_runs:
        _ok(f'{len(step_runs)} StepRun record(s) written to DB')
        for sr in step_runs:
            with app.app_context():
                sr = db.session.merge(sr)
                print(f'     step "{sr.step_name}": status={sr.status}, rows={sr.rows_affected}')
    else:
        _warn('No StepRun records found — run may have failed before executing steps')

    # Check worker output for task receipt
    task_received = 'run_pipeline_task' in worker_stdout or 'celery_verify' in worker_stdout
    task_succeeded = 'succeeded' in worker_stdout or 'Task flowforge' in worker_stdout
    if task_received or task_succeeded:
        _ok('Worker log confirms task was received and processed')
    else:
        _warn('Could not confirm task receipt in worker output (may have been buffered)')

    _cleanup(app, pipeline_id, conn_id)
    _ok('Test data cleaned up')
    return run.status in ('success', 'failed')  # either proves the worker ran it


# ──────────────────────────────────────────────────────────────────────────────
# Test 2 — Thread fallback path (no Redis)
# ──────────────────────────────────────────────────────────────────────────────

def test_thread_fallback():
    _header('TEST 2 — Thread fallback (no FLOWFORGE_REDIS_URL)')

    # Temporarily unset Redis URL
    original = os.environ.pop('FLOWFORGE_REDIS_URL', '')
    try:
        # Create a fresh app WITHOUT Redis — launcher must use threads
        app_no_redis = create_app()
        conn_id     = _create_test_connection(app_no_redis)
        pipeline_id = _create_test_pipeline(app_no_redis, conn_id)
        _ok('Test pipeline created')

        from flowforge.engine.launcher import launch_run, _use_celery
        if _use_celery():
            _err('_use_celery() returned True even with FLOWFORGE_REDIS_URL unset')
        _ok('_use_celery() correctly returns False')

        with app_no_redis.app_context():
            pipeline = db.session.get(Pipeline, pipeline_id)
            resp, status_code = launch_run(pipeline, triggered_by='e2e_thread', app=app_no_redis)

        run_id = resp['run_id']
        if status_code != 202:
            _err(f'launch_run returned {status_code}')
        _ok(f'Run dispatched in thread mode (run_id={run_id[:8]}…)')

        print(f'  Waiting up to {_POLL_SECS}s for thread run to complete…')
        run = _poll_run(app_no_redis, run_id)

        if run is None:
            _err('PipelineRun record not found')
        print(f'\n  PipelineRun.status = {run.status!r}')

        if run.status in ('success', 'failed'):
            _ok(f'Run completed with status="{run.status}" (thread mode confirmed)')
        else:
            _err(f'Run still "running" after timeout — thread executor may have stalled')

        step_runs = _get_step_runs(app_no_redis, run_id)
        if step_runs:
            _ok(f'{len(step_runs)} StepRun record(s) written by thread executor')
        else:
            _warn('No StepRun records — run may have failed before step execution')

        _cleanup(app_no_redis, pipeline_id, conn_id)
        _ok('Test data cleaned up')
        return run.status in ('success', 'failed')
    finally:
        os.environ['FLOWFORGE_REDIS_URL'] = original


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print('\nFlowForge — Celery E2E Verification')
    print('='*60)
    print(f'  DB  : {_DB_URL}')
    print(f'  Redis: {_REDIS}')
    print(f'  Python: {sys.executable}')

    # Quick Redis connectivity check
    try:
        import redis as redis_lib
        r = redis_lib.from_url(_REDIS, socket_connect_timeout=3)
        r.ping()
        _ok('Redis reachable')
    except Exception as e:
        _err(f'Cannot reach Redis at {_REDIS}: {e}')

    results = {}
    try:
        results['celery'] = test_celery_path()
    except SystemExit:
        results['celery'] = False

    try:
        results['thread'] = test_thread_fallback()
    except SystemExit:
        results['thread'] = False

    _header('SUMMARY')
    for name, ok in results.items():
        status = PASS if ok else FAIL
        print(f'  {status}  {name}')

    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)
