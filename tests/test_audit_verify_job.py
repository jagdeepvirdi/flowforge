"""The scheduled audit-chain verification: it runs, records, alerts, and never fails silently."""
import json
import logging
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import text

from flowforge import audit, audit_chain
from flowforge.db.models import db
from flowforge.engine import scheduler as sched

WEBHOOK = 'https://alerts.example.com/hook/secret-token'


@pytest.fixture(autouse=True)
def _clean(app, monkeypatch):
    def wipe():
        with app.app_context(), db.engine.begin() as conn:
            conn.execute(text("SELECT set_config('flowforge.audit_maintenance', 'on', true)"))
            conn.execute(text('TRUNCATE ff_audit_log'))
    wipe()
    monkeypatch.setattr(sched, '_app', app)
    monkeypatch.delenv('FLOWFORGE_AUDIT_ALERT_WEBHOOK_URL', raising=False)
    yield
    wipe()


def _write(app, n=5):
    with app.app_context():
        for i in range(n):
            audit._write_db_audit('TEST_ACTION', 'alice', None, '10.0.0.1', {'i': i})


def _tamper(app, sql):
    with app.app_context(), db.engine.begin() as conn:
        conn.execute(text("SELECT set_config('flowforge.audit_maintenance', 'on', true)"))
        conn.execute(text(sql))


def _events(app):
    with app.app_context():
        return db.session.execute(text(
            "SELECT action, username, details FROM ff_audit_log WHERE action LIKE 'AUDIT_CHAIN_%' ORDER BY seq NULLS LAST"
        )).all()


def _verify_ok(app):
    with app.app_context(), db.engine.connect() as conn:
        return audit_chain.verify(conn)


# -- the job ----------------------------------------------------------------------------------

def test_a_healthy_chain_is_recorded_and_raises_no_alert(app, monkeypatch):
    monkeypatch.setenv('FLOWFORGE_AUDIT_ALERT_WEBHOOK_URL', WEBHOOK)
    _write(app, 5)
    with patch('flowforge.engine.notifications._fire_failure_webhook') as hook:
        sched._verify_audit_chain_job()
    hook.assert_not_called()
    [(action, user, d)] = _events(app)
    assert action == 'AUDIT_CHAIN_VERIFIED' and user == 'system'
    assert d['ok'] is True and d['chained_rows'] == 5 and d['problem_count'] == 0
    assert _verify_ok(app).ok                                       # the record itself is chained, chain still valid


def test_tampering_is_recorded_logged_and_sent_to_the_webhook_without_leaking_values(app, monkeypatch, caplog):
    monkeypatch.setenv('FLOWFORGE_AUDIT_ALERT_WEBHOOK_URL', WEBHOOK)
    _write(app, 6)
    _tamper(app, "UPDATE ff_audit_log SET username = 'mallory', ip_address = '6.6.6.6' WHERE seq = 3")
    audit.logging.getLogger('flowforge.audit').propagate = True
    with patch('flowforge.engine.notifications._fire_failure_webhook') as hook, \
         caplog.at_level(logging.ERROR, logger='flowforge.audit'):
        sched._verify_audit_chain_job()

    [(action, _, d)] = _events(app)
    assert action == 'AUDIT_CHAIN_VERIFY_FAILED' and d['ok'] is False
    assert any('seq 3' in p for p in d['problems'])

    hook.assert_called_once()
    url, payload = hook.call_args.args
    assert url == WEBHOOK
    assert payload['event'] == 'audit_chain_verification_failed' and payload['severity'] == 'critical'
    assert 'FAILED' in payload['text'] and payload['problem_count'] >= 1
    assert payload['tail'] and payload['chained_rows'] == 6
    blob = json.dumps(payload) + json.dumps(d)
    assert 'mallory' not in blob and '6.6.6.6' not in blob          # no actor names, no IPs, no field values
    assert any('CHAIN VERIFY FAILED' in r.getMessage() for r in caplog.records)


def test_without_a_webhook_a_failure_is_still_recorded_and_logged(app):
    _write(app, 4)
    _tamper(app, 'DELETE FROM ff_audit_log WHERE seq = 2')
    with patch('flowforge.engine.notifications._fire_failure_webhook') as hook:
        sched._verify_audit_chain_job()
    hook.assert_not_called()
    assert [e[0] for e in _events(app)] == ['AUDIT_CHAIN_VERIFY_FAILED']


def test_a_verifier_that_crashes_is_alerted_as_a_failure_not_swallowed(app, monkeypatch):
    monkeypatch.setenv('FLOWFORGE_AUDIT_ALERT_WEBHOOK_URL', WEBHOOK)
    _write(app, 3)
    with patch.object(audit_chain, 'verify', side_effect=RuntimeError('connection reset')), \
         patch('flowforge.engine.notifications._fire_failure_webhook') as hook:
        sched._verify_audit_chain_job()                              # must not raise
    [(action, _, d)] = _events(app)
    assert action == 'AUDIT_CHAIN_VERIFY_FAILED'
    assert 'verification could not run: RuntimeError: connection reset' in d['problems'][0]
    hook.assert_called_once()


def test_with_no_key_the_failure_is_still_recorded_and_alerted(app, monkeypatch):
    _write(app, 3)
    monkeypatch.setenv('FLOWFORGE_AUDIT_ALERT_WEBHOOK_URL', WEBHOOK)
    monkeypatch.delenv('FLOWFORGE_SECRET_KEY')
    monkeypatch.delenv('FLOWFORGE_AUDIT_CHAIN_KEY', raising=False)
    with patch('flowforge.engine.notifications._fire_failure_webhook') as hook:
        sched._verify_audit_chain_job()
    monkeypatch.undo()
    assert [e[0] for e in _events(app)] == ['AUDIT_CHAIN_VERIFY_FAILED']
    assert any('cannot verify' in p for p in _events(app)[0][2]['problems'])
    hook.assert_called_once()


def test_a_webhook_aimed_at_a_private_address_is_blocked_and_does_not_break_the_job(app, monkeypatch):
    monkeypatch.setenv('FLOWFORGE_AUDIT_ALERT_WEBHOOK_URL', 'http://127.0.0.1:9/hook')   # real sender: SSRF guard
    _write(app, 3)
    _tamper(app, "UPDATE ff_audit_log SET username = 'x' WHERE seq = 2")
    sched._verify_audit_chain_job()
    assert [e[0] for e in _events(app)] == ['AUDIT_CHAIN_VERIFY_FAILED']


def test_the_job_does_nothing_without_an_app(monkeypatch):
    monkeypatch.setattr(sched, '_app', None)
    with patch.object(audit_chain, 'verify') as v:
        sched._verify_audit_chain_job()
    v.assert_not_called()


def test_repeated_runs_each_leave_a_record_and_keep_the_chain_valid(app):
    _write(app, 3)
    for _ in range(3):
        sched._verify_audit_chain_job()
    assert [e[0] for e in _events(app)] == ['AUDIT_CHAIN_VERIFIED'] * 3
    assert _verify_ok(app).ok


# -- scheduling -------------------------------------------------------------------------------

def _registered(monkeypatch, env):
    fake = MagicMock()
    monkeypatch.setattr(sched, '_scheduler', fake)
    for k in ('FLOWFORGE_AUDIT_VERIFY_CRON',):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    sched._register_audit_verify_job()
    return fake


def _fields(trigger):
    return {f.name: str(f) for f in trigger.fields}


def test_default_schedule_is_daily_at_0300_utc_after_the_prune(monkeypatch):
    fake = _registered(monkeypatch, {})
    kw = fake.add_job.call_args.kwargs
    assert fake.add_job.call_args.args[0] is sched._verify_audit_chain_job
    assert kw['id'] == 'audit_chain_verify' and kw['replace_existing'] and kw['max_instances'] == 1 and kw['coalesce']
    f = _fields(kw['trigger'])
    assert (f['hour'], f['minute']) == ('3', '0')
    assert str(kw['trigger'].timezone) == 'UTC'


def test_a_custom_cron_is_honoured(monkeypatch):
    fake = _registered(monkeypatch, {'FLOWFORGE_AUDIT_VERIFY_CRON': '*/30 * * * *'})
    assert _fields(fake.add_job.call_args.kwargs['trigger'])['minute'] == '*/30'


@pytest.mark.parametrize('bad', ['every day', '99 * * * *', '* * *', 'garbage'])
def test_a_bad_cron_falls_back_to_the_default_instead_of_disabling_the_check(monkeypatch, caplog, bad):
    with caplog.at_level(logging.ERROR, logger='flowforge.engine.scheduler'):
        fake = _registered(monkeypatch, {'FLOWFORGE_AUDIT_VERIFY_CRON': bad})
    f = _fields(fake.add_job.call_args.kwargs['trigger'])
    assert (f['hour'], f['minute']) == ('3', '0')
    assert any('not a valid' in r.getMessage() for r in caplog.records)


@pytest.mark.parametrize('off', ['off', 'OFF', 'false', 'disabled', 'none'])
def test_only_an_explicit_off_disables_it_and_removes_a_persisted_job(monkeypatch, caplog, off):
    with caplog.at_level(logging.WARNING, logger='flowforge.engine.scheduler'):
        fake = _registered(monkeypatch, {'FLOWFORGE_AUDIT_VERIFY_CRON': off})
    fake.add_job.assert_not_called()
    fake.remove_job.assert_called_once_with('audit_chain_verify')
    assert any('DISABLED' in r.getMessage() for r in caplog.records)


def test_disabling_when_the_job_was_never_stored_is_fine(monkeypatch):
    fake = MagicMock()
    fake.remove_job.side_effect = JobLookupError('audit_chain_verify')
    monkeypatch.setattr(sched, '_scheduler', fake)
    monkeypatch.setenv('FLOWFORGE_AUDIT_VERIFY_CRON', 'off')
    sched._register_audit_verify_job()                               # no exception


def test_an_empty_setting_means_the_default_not_off(monkeypatch):
    fake = _registered(monkeypatch, {'FLOWFORGE_AUDIT_VERIFY_CRON': '  '})
    assert fake.add_job.called


def test_the_job_registers_in_a_real_scheduler_and_fires_at_the_next_0300(monkeypatch):
    real = BackgroundScheduler(timezone='UTC')
    monkeypatch.setattr(sched, '_scheduler', real)
    monkeypatch.delenv('FLOWFORGE_AUDIT_VERIFY_CRON', raising=False)
    sched._register_audit_verify_job()
    [job] = real.get_jobs()
    assert job.id == 'audit_chain_verify'
    nxt = job.trigger.get_next_fire_time(None, datetime.now(UTC))
    assert (nxt.hour, nxt.minute) == (3, 0)


def test_start_scheduler_registers_the_verify_job():
    mock_app = MagicMock()
    mock_app.app_context.return_value.__enter__ = MagicMock(return_value=None)
    mock_app.app_context.return_value.__exit__ = MagicMock(return_value=False)
    fake = MagicMock()
    fake.start.side_effect = KeyboardInterrupt
    with patch('flowforge.engine.scheduler.BlockingScheduler', return_value=fake), \
         patch('flowforge.engine.scheduler._sync_pipeline_jobs'), \
         patch('flowforge.engine.scheduler._register_cleanup_job'), \
         patch('flowforge.engine.scheduler._register_sync_job'), \
         patch.dict('os.environ', {'FLOWFORGE_DB_URL': ''}):
        try:
            sched.start_scheduler(mock_app)
        except (KeyboardInterrupt, SystemExit):
            pass
    assert any(c.kwargs.get('id') == 'audit_chain_verify' for c in fake.add_job.call_args_list)
