"""Real crash-recovery test for the scheduler's persistent jobstore.

test_scheduler.py mocks the scheduler and jobstore entirely, so it can't
verify the claim scheduler.py logs on startup: "jobstore: PostgreSQL — jobs
survive scheduler restarts." This test exercises a real
apscheduler.jobstores.sqlalchemy.SQLAlchemyJobStore against the real test
Postgres DB, with a *hard* simulated crash (the first scheduler instance is
simply dropped, never given a chance to run a graceful shutdown() — a real
process kill doesn't call shutdown hooks either) — proving jobs genuinely
persist across process death, not just clean restarts.

An earlier draft of this test got a false negative: calling add_job() on a
scheduler that was never .start()ed doesn't write through to the jobstore at
all (jobs sit in an in-memory pending list). Both scheduler instances below
must be .start()ed, matching what flowforge.engine.scheduler.start_scheduler()
actually does in production.
"""
import os
import time

import pytest
import sqlalchemy as sa
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler

_TABLE = 'test_probe_jobs'


def _dummy_job():
    pass


@pytest.fixture
def db_url():
    url = os.environ['FLOWFORGE_DB_URL']
    yield url
    eng = sa.create_engine(url)
    with eng.begin() as conn:
        conn.execute(sa.text(f'DROP TABLE IF EXISTS {_TABLE}'))
    eng.dispose()


def test_job_survives_hard_crash_of_scheduler_process(db_url):
    sched_a = BackgroundScheduler(jobstores={'default': SQLAlchemyJobStore(url=db_url, tablename=_TABLE)})
    sched_a.start()
    try:
        sched_a.add_job(_dummy_job, trigger='cron', hour=8, id='probe_job', replace_existing=True)
        time.sleep(0.3)
        assert any(j.id == 'probe_job' for j in sched_a.get_jobs())
    finally:
        # No sched_a.shutdown() — simulates a hard process kill, not a clean restart.
        del sched_a

    sched_b = BackgroundScheduler(jobstores={'default': SQLAlchemyJobStore(url=db_url, tablename=_TABLE)})
    sched_b.start()
    try:
        time.sleep(0.3)
        jobs = sched_b.get_jobs()
        assert any(j.id == 'probe_job' for j in jobs), (
            'job did not survive a simulated hard crash — the "jobs survive scheduler '
            'restarts" claim in scheduler.py does not hold'
        )
    finally:
        sched_b.shutdown(wait=False)


def test_job_update_from_crashed_process_is_not_lost(db_url):
    """A job re-registered with replace_existing right before a crash must
    still reflect the latest schedule after recovery (not a stale earlier one)."""
    sched_a = BackgroundScheduler(jobstores={'default': SQLAlchemyJobStore(url=db_url, tablename=_TABLE)})
    sched_a.start()
    try:
        sched_a.add_job(_dummy_job, trigger='cron', hour=8, id='probe_job', replace_existing=True)
        time.sleep(0.2)
        sched_a.add_job(_dummy_job, trigger='cron', hour=14, id='probe_job', replace_existing=True)
        time.sleep(0.3)
    finally:
        del sched_a

    sched_b = BackgroundScheduler(jobstores={'default': SQLAlchemyJobStore(url=db_url, tablename=_TABLE)})
    sched_b.start()
    try:
        time.sleep(0.3)
        job = sched_b.get_job('probe_job')
        assert job is not None
        assert "hour='14'" in str(job.trigger), f'expected hour=14 trigger after recovery, got: {job.trigger}'
    finally:
        sched_b.shutdown(wait=False)
