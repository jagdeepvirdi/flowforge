"""
Scheduler diagnostic script -- run with: python check_scheduler.py

Tests each layer independently:
  1. Env vars present
  2. DB reachable
  3. Pipelines with schedules found
  4. App context works from a worker thread (the core fix)
  5. Directly fires _run_pipeline_job for the first scheduled pipeline
  6. Run history check
  7. APScheduler job registration check
"""
import os
import sys
import threading
import time

# Force UTF-8 output so ANSI and box chars work on Windows
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

load_dotenv()

PASS = "[PASS]"
FAIL = "[FAIL]"
INFO = "[INFO]"
SEP  = "-" * 55

def section(title):
    print(f"\n{SEP}\n  {title}\n{SEP}")

# ── 1. Env vars ─────────────────────────────────────────────
section("1. Environment variables")
db_url = os.environ.get("FLOWFORGE_DB_URL", "")
secret  = os.environ.get("FLOWFORGE_SECRET_KEY", "")
print(f"  FLOWFORGE_DB_URL    : {'set (' + db_url[:50] + ')' if db_url else 'MISSING'}")
print(f"  FLOWFORGE_SECRET_KEY: {'set' if secret else 'MISSING'}")
if not db_url:
    print(f"{FAIL} FLOWFORGE_DB_URL not set -- scheduler cannot connect to DB.")
    sys.exit(1)

# ── 2. DB reachable ─────────────────────────────────────────
section("2. Database connectivity")
try:
    from flowforge.api.app import create_app
    app = create_app()
    with app.app_context():
        from flowforge.db.models import db
        db.session.execute(db.text("SELECT 1"))
    print(f"{PASS} Database reachable")
except Exception as e:
    print(f"{FAIL} Cannot reach database: {e}")
    sys.exit(1)

# ── 3. Scheduled pipelines in DB ────────────────────────────
section("3. Pipelines with schedules")
with app.app_context():
    from flowforge.db.models import Pipeline
    pipelines = db.session.query(Pipeline).filter(
        Pipeline.enabled.is_(True),
        Pipeline.schedule.isnot(None),
        Pipeline.schedule != "",
    ).all()

if not pipelines:
    print(f"{FAIL} No enabled pipelines with a schedule found.")
    print("  --> Go to the Pipeline editor, set a cron schedule, enable the pipeline.")
    sys.exit(1)

for p in pipelines:
    print(f"{PASS} '{p.name}'  schedule='{p.schedule}'  enabled={p.enabled}")

target = pipelines[0]

# ── 4. App context from worker thread ───────────────────────
section("4. App context from worker thread (the critical fix)")
thread_result = {"ok": False, "error": ""}

import flowforge.engine.scheduler as sched_module

sched_module._app = app   # simulate what start_scheduler() does

def thread_test():
    try:
        with sched_module._app.app_context():
            from flowforge.db.models import Pipeline as P
            from flowforge.db.models import db as d
            d.session.query(P).count()
            thread_result["ok"] = True
    except Exception as e:
        thread_result["error"] = str(e)

t = threading.Thread(target=thread_test)
t.start()
t.join(timeout=10)

if thread_result["ok"]:
    print(f"{PASS} App context created successfully from worker thread")
else:
    print(f"{FAIL} App context failed in worker thread: {thread_result['error']}")
    sys.exit(1)

# ── 5. Fire _run_pipeline_job directly ──────────────────────
section(f"5. Direct job execution -- '{target.name}'")
print(f"  Firing _run_pipeline_job for pipeline: {target.name}")
print("  (same call APScheduler makes when the cron fires)\n")

import logging

logging.basicConfig(
    level=logging.INFO,
    format="  %(levelname)-8s %(name)s -- %(message)s",
    stream=sys.stdout,
)
for noisy in ("apscheduler", "werkzeug", "sqlalchemy.engine"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

fire_result = {"done": False, "error": ""}

def fire_job():
    try:
        sched_module._run_pipeline_job(target.id, target.name)
        fire_result["done"] = True
    except Exception as e:
        fire_result["error"] = str(e)

t2 = threading.Thread(target=fire_job)
t2.start()
t2.join(timeout=60)

if not t2.is_alive() and fire_result["done"]:
    print(f"\n{PASS} _run_pipeline_job completed without error")
elif not t2.is_alive() and fire_result["error"]:
    print(f"\n{FAIL} _run_pipeline_job raised: {fire_result['error']}")
else:
    print(f"\n{INFO} Job still running after 60s (long pipeline?)")

# ── 6. Run history ───────────────────────────────────────────
section("6. Run history (last 3 runs for this pipeline)")
time.sleep(1)
with app.app_context():
    from flowforge.db.models import PipelineRun
    runs = (db.session.query(PipelineRun)
            .filter_by(pipeline_id=target.id)
            .order_by(PipelineRun.started_at.desc())
            .limit(3).all())
    if runs:
        for r in runs:
            print(f"  {r.status.upper():<10} triggered_by={r.triggered_by:<12} started={r.started_at}")
    else:
        print(f"  No runs found for '{target.name}'")

# ── 7. APScheduler job registration ─────────────────────────
section("7. APScheduler job registration (what would be scheduled)")
from datetime import UTC, datetime

with app.app_context():
    from flowforge.db.models import Pipeline as _P
    scheduled = [
        p for p in db.session.query(_P).filter_by(enabled=True).all()
        if p.schedule and len(p.schedule.strip().split()) == 5
    ]

if scheduled:
    now = datetime.now(UTC)
    for p in scheduled:
        print(f"  pipeline_{p.id}")
        print(f"    pipeline : {p.name}")
        print(f"    cron     : {p.schedule}")
else:
    print(f"{FAIL} No jobs would be registered -- scheduler would do nothing")

print(f"\n{SEP}")
print("  Diagnostic complete.")
print("  If all steps passed, run the scheduler in a SEPARATE terminal with:")
print("    flowforge schedule")
print("  Watch that terminal for log lines like:")
print("    INFO ... -- Scheduled 'My Pipeline': 0 * * * *")
print("    INFO ... -- [My Pipeline] Starting step: ...")
print(SEP)
