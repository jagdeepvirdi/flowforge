"""Is the scheduled audit verification still running? Heartbeat (push) and status (pull)."""
import json
import logging
import re
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import bcrypt
import pytest
from click.testing import CliRunner
from sqlalchemy import text

from flowforge import audit, audit_chain
from flowforge.db.models import User, db
from flowforge.engine import notifications
from flowforge.engine import scheduler as sched
from flowforge.net_guard import UnsafeUrlError

BEAT = 'https://hc-ping.example.com/9f8e7d6c-secret-uuid'


@pytest.fixture(autouse=True)
def _clean(app, monkeypatch):
    def wipe():
        with app.app_context(), db.engine.begin() as conn:
            conn.execute(text("SELECT set_config('flowforge.audit_maintenance', 'on', true)"))
            conn.execute(text('TRUNCATE ff_audit_log'))
    wipe()
    monkeypatch.setattr(sched, '_app', app)
    for k in ('FLOWFORGE_AUDIT_HEARTBEAT_URL', 'FLOWFORGE_AUDIT_ALERT_WEBHOOK_URL', 'FLOWFORGE_AUDIT_VERIFY_CRON',
              'FLOWFORGE_AUDIT_VERIFY_MAX_AGE_HOURS'):
        monkeypatch.delenv(k, raising=False)
    yield
    wipe()


def _add(app, action, hours_ago, ok=True, problems=0, unchained=False):
    ts = datetime.now(UTC) - timedelta(hours=hours_ago)
    with app.app_context(), db.engine.begin() as conn:
        if unchained:
            conn.execute(text("INSERT INTO ff_audit_log (id, timestamp, action, username, details) "
                              "VALUES (:id, :t, :a, 'system', CAST(:d AS JSONB))"),
                         {'id': str(uuid.uuid4()), 't': ts, 'a': action, 'd': json.dumps({'ok': ok})})
        else:
            audit_chain.append(conn, action, 'system', None, '', {'ok': ok, 'problem_count': problems}, ts=ts)


def _status(app):
    with app.app_context(), db.engine.connect() as conn:
        return audit_chain.verification_status(conn)


VERIFIED, FAILED = 'AUDIT_CHAIN_VERIFIED', 'AUDIT_CHAIN_VERIFY_FAILED'


# -- the staleness threshold ------------------------------------------------------------------

@pytest.mark.parametrize('cron,hours', [
    ('0 3 * * *', 37.0),          # daily: 24 * 1.5 + 1
    ('*/30 * * * *', 1.75),       # every 30 min: 0.5 * 1.5 + 1
    ('0 3 * * 1', 253.0),         # weekly: 168 * 1.5 + 1
    ('0 3 * * 1,4', 145.0),       # Mon and Thu: the longest gap is 4 days, not the average
])
def test_the_limit_is_derived_from_the_schedule(monkeypatch, cron, hours):
    monkeypatch.setenv('FLOWFORGE_AUDIT_VERIFY_CRON', cron)
    assert audit_chain.expected_max_age().total_seconds() / 3600 == pytest.approx(hours)


def test_the_default_schedule_gives_37_hours():
    assert audit_chain.expected_max_age().total_seconds() / 3600 == pytest.approx(37.0)


def test_an_override_wins_but_a_bad_one_is_ignored(monkeypatch):
    monkeypatch.setenv('FLOWFORGE_AUDIT_VERIFY_MAX_AGE_HOURS', '5')
    assert audit_chain.expected_max_age() == timedelta(hours=5)
    for bad in ('abc', '0', '-3', ''):
        monkeypatch.setenv('FLOWFORGE_AUDIT_VERIFY_MAX_AGE_HOURS', bad)
        assert audit_chain.expected_max_age().total_seconds() / 3600 == pytest.approx(37.0)


def test_switched_off_means_no_limit_even_with_an_override(monkeypatch):
    monkeypatch.setenv('FLOWFORGE_AUDIT_VERIFY_CRON', 'off')
    monkeypatch.setenv('FLOWFORGE_AUDIT_VERIFY_MAX_AGE_HOURS', '5')
    assert audit_chain.expected_max_age() is None


# -- the status -------------------------------------------------------------------------------

def test_a_fresh_install_is_pending_not_an_alarm(app):
    assert _status(app)['state'] == 'pending' and _status(app)['healthy']
    _add(app, 'TEST_ACTION', hours_ago=2)
    st = _status(app)
    assert st['state'] == 'pending' and st['healthy'] and st['last_run_at'] is None


def test_an_old_log_with_no_verification_ever_recorded_is_flagged(app):
    _add(app, 'TEST_ACTION', hours_ago=80)
    st = _status(app)
    assert st['state'] == 'never' and not st['healthy']


def test_a_recent_passing_verification_is_ok(app):
    _add(app, VERIFIED, hours_ago=3)
    st = _status(app)
    assert st['state'] == 'ok' and st['healthy'] and st['last_ok'] is True
    assert st['age_hours'] == pytest.approx(3, abs=0.1) and st['max_age_hours'] == pytest.approx(37)


@pytest.mark.parametrize('hours,state', [(36, 'ok'), (38, 'stale'), (200, 'stale')])
def test_an_overdue_verification_is_stale(app, hours, state):
    _add(app, VERIFIED, hours_ago=hours)
    st = _status(app)
    assert st['state'] == state and st['healthy'] == (state == 'ok')


def test_a_failed_verification_is_unhealthy_however_recent(app):
    _add(app, FAILED, hours_ago=1, ok=False, problems=4)
    st = _status(app)
    assert st['state'] == 'failed' and not st['healthy'] and st['problem_count'] == 4


def test_the_newest_record_decides(app):
    _add(app, FAILED, hours_ago=30, ok=False)
    _add(app, VERIFIED, hours_ago=2)
    assert _status(app)['state'] == 'ok'
    _add(app, FAILED, hours_ago=1, ok=False)
    assert _status(app)['state'] == 'failed'


def test_a_hand_inserted_unchained_verified_row_cannot_hide_a_dead_scheduler(app):
    _add(app, VERIFIED, hours_ago=100)
    _add(app, VERIFIED, hours_ago=0.1, unchained=True)               # forged: no chain, no key
    st = _status(app)
    assert st['state'] == 'stale' and st['age_hours'] > 90


def test_when_switched_off_the_status_says_disabled_and_is_not_an_alarm(app, monkeypatch):
    monkeypatch.setenv('FLOWFORGE_AUDIT_VERIFY_CRON', 'off')
    st = _status(app)
    assert st['state'] == 'disabled' and st['healthy'] and st['max_age_hours'] is None


def test_the_real_job_leaves_a_record_the_status_accepts(app):
    with app.app_context():
        audit._write_db_audit('TEST_ACTION', 'alice', None, '', {})
    sched._verify_audit_chain_job()
    st = _status(app)
    assert st['state'] == 'ok' and st['age_hours'] < 0.1


# -- the heartbeat ----------------------------------------------------------------------------

def _run_job(app, monkeypatch, beat=BEAT, tamper=False, crash=False):
    if beat:
        monkeypatch.setenv('FLOWFORGE_AUDIT_HEARTBEAT_URL', beat)
    with app.app_context():
        for i in range(3):
            audit._write_db_audit('TEST_ACTION', 'alice', None, '', {'i': i})
    if tamper:
        with app.app_context(), db.engine.begin() as conn:
            conn.execute(text("SELECT set_config('flowforge.audit_maintenance', 'on', true)"))
            conn.execute(text("UPDATE ff_audit_log SET username = 'mallory' WHERE seq = 2"))
    with patch('flowforge.engine.notifications._ping_heartbeat') as ping:
        if crash:
            with patch.object(audit_chain, 'verify', side_effect=RuntimeError('db gone')):
                sched._verify_audit_chain_job()
        else:
            sched._verify_audit_chain_job()
    return ping


def test_a_passing_check_pings_the_heartbeat(app, monkeypatch):
    ping = _run_job(app, monkeypatch)
    ping.assert_called_once_with(BEAT)


def test_a_failing_check_does_not_ping_so_the_monitor_alerts(app, monkeypatch):
    _run_job(app, monkeypatch, tamper=True).assert_not_called()


def test_a_crashed_verifier_does_not_ping(app, monkeypatch):
    _run_job(app, monkeypatch, crash=True).assert_not_called()


def test_without_a_heartbeat_url_nothing_is_pinged(app, monkeypatch):
    _run_job(app, monkeypatch, beat=None).assert_not_called()


def test_the_alert_webhook_and_the_heartbeat_are_independent(app, monkeypatch):
    monkeypatch.setenv('FLOWFORGE_AUDIT_ALERT_WEBHOOK_URL', 'https://alerts.example.com/x')
    with patch('flowforge.engine.notifications._fire_failure_webhook') as hook:
        ping = _run_job(app, monkeypatch, tamper=True)
    hook.assert_called_once()
    ping.assert_not_called()


def test_a_broken_ping_never_breaks_the_job(app, monkeypatch):
    monkeypatch.setenv('FLOWFORGE_AUDIT_HEARTBEAT_URL', BEAT)
    with app.app_context():
        audit._write_db_audit('TEST_ACTION', 'alice', None, '', {})
    with patch('flowforge.net_guard.safe_urlopen', side_effect=OSError('network down')):
        sched._verify_audit_chain_job()
    assert _status(app)['state'] == 'ok'                              # recorded; the ping just failed


# -- the ping itself --------------------------------------------------------------------------

def test_ping_delivers_a_plain_get_through_the_guarded_opener():
    cm = MagicMock()
    with patch('flowforge.net_guard.safe_urlopen', return_value=cm) as opener:
        assert notifications._ping_heartbeat(BEAT) is True
    opener.assert_called_once_with(BEAT, timeout=10)                  # a URL string => GET, no body
    cm.__enter__.assert_called_once()


@pytest.mark.parametrize('exc', [
    HTTPError(BEAT, 500, 'boom', {}, None), URLError('refused'), UnsafeUrlError('private address'), OSError('x'),
])
def test_ping_failures_are_logged_never_raised(exc, caplog):
    with patch('flowforge.net_guard.safe_urlopen', side_effect=exc), caplog.at_level(logging.WARNING):
        assert notifications._ping_heartbeat(BEAT) is False
    hosts = {m.group(1) for r in caplog.records if (m := re.match(r'Heartbeat ping to (\S+) ', r.getMessage()))}
    assert hosts == {'hc-ping.example.com'}            # exactly the host, and nothing from the path


def test_the_secret_in_the_url_is_never_logged(caplog):
    with patch('flowforge.net_guard.safe_urlopen', side_effect=OSError('x')), caplog.at_level(logging.DEBUG):
        notifications._ping_heartbeat(BEAT)
    with patch('flowforge.net_guard.safe_urlopen', return_value=MagicMock()), caplog.at_level(logging.DEBUG):
        notifications._ping_heartbeat(BEAT)
    assert 'secret-uuid' not in caplog.text and '9f8e7d6c' not in caplog.text


def test_ping_to_a_private_address_is_refused_by_the_real_guard():
    assert notifications._ping_heartbeat('http://127.0.0.1:9/ping') is False
    assert notifications._ping_heartbeat('') is False


# -- CLI and API ------------------------------------------------------------------------------

def test_cli_status_exit_codes_and_json(app):
    from flowforge.cli import cli
    with patch('flowforge.cli._create_app', return_value=app):
        _add(app, VERIFIED, hours_ago=2)
        good = CliRunner().invoke(cli, ['audit', 'status'])
        assert good.exit_code == 0 and good.output.startswith('OK')
        as_json = CliRunner().invoke(cli, ['audit', 'status', '--json'])
        assert json.loads(as_json.output)['state'] == 'ok'
        _add(app, FAILED, hours_ago=1, ok=False, problems=2)
        bad = CliRunner().invoke(cli, ['audit', 'status'])
        assert bad.exit_code == 1 and bad.output.startswith('FAILED')


def test_cli_status_flags_a_dead_scheduler(app):
    from flowforge.cli import cli
    _add(app, VERIFIED, hours_ago=90)
    with patch('flowforge.cli._create_app', return_value=app):
        out = CliRunner().invoke(cli, ['audit', 'status'])
    assert out.exit_code == 1 and out.output.startswith('STALE') and 'not running' in out.output


def test_status_endpoint_is_admin_only_and_reports_state(app, client, headers):
    _add(app, VERIFIED, hours_ago=2)
    ok = client.get('/api/audit-logs/verify/status', headers=headers)
    assert ok.status_code == 200
    body = ok.get_json()
    assert body['state'] == 'ok' and body['healthy'] is True and body['max_age_hours'] == pytest.approx(37)
    assert client.get('/api/audit-logs/verify/status').status_code == 401

    name = f'hb_{uuid.uuid4().hex[:6]}'
    with app.app_context():
        db.session.add(User(username=name, role='viewer', password_hash=bcrypt.hashpw(b'pw-x', bcrypt.gensalt(4)).decode()))
        db.session.commit()
    login = client.post('/api/auth/login', json={'username': name, 'password': 'pw-x'})
    viewer = {'Authorization': f'Bearer {login.get_json()["token"]}'}
    try:
        assert client.get('/api/audit-logs/verify/status', headers=viewer).status_code == 403
    finally:
        with app.app_context():
            u = db.session.query(User).filter_by(username=name).first()
            if u:
                db.session.delete(u)
                db.session.commit()
