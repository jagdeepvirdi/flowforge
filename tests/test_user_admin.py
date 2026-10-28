"""Tests for flowforge/user_admin.py and the `flowforge user` CLI.

The point of this feature: no password has to be typed into a config file or passed on a
command line. Passwords are generated (printed once) or prompted for, and only the bcrypt
hash is stored.
"""
import json
import uuid
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from flowforge import cli as cli_module
from flowforge.db.models import AuditLog, User, db
from flowforge.user_admin import MIN_PASSWORD_LEN, create_user, delete_user, generate_password


def _name(prefix='ua'):
    return f'{prefix}_{uuid.uuid4().hex[:8]}'


def _login(client, username, password):
    return client.post('/api/auth/login', json={'username': username, 'password': password})


@pytest.fixture
def runner(app):
    """CliRunner whose commands run against the test app (instead of building their own)."""
    with patch.object(cli_module, '_create_app', return_value=app):
        yield CliRunner()


def _cleanup(app, *usernames):
    with app.app_context():
        for u in usernames:
            delete_user(u)


# ── module ────────────────────────────────────────────────────────────────────


def test_generate_password_is_strong_and_unique():
    a, b = generate_password(), generate_password()
    assert a != b
    assert len(a) >= 20


def test_created_user_with_generated_password_can_log_in(app, client):
    name = _name()
    with app.app_context():
        user, password = create_user(name, role='editor', must_change_password=False)
        assert user.password_hash.startswith('$2')           # bcrypt hash, not the password
        assert password not in user.password_hash
    try:
        resp = _login(client, name, password)
        assert resp.status_code == 200
        assert 'token' in resp.get_json()
    finally:
        _cleanup(app, name)


def test_generated_user_must_change_password_by_default(app, client):
    name = _name()
    with app.app_context():
        _, password = create_user(name, role='editor')
    try:
        body = _login(client, name, password).get_json()
        assert body.get('password_change_required') is True
        assert 'token' not in body
    finally:
        _cleanup(app, name)


@pytest.mark.parametrize('kwargs,message', [
    ({'username': ''}, 'username is required'),
    ({'username': 'x', 'role': 'root'}, 'role must be one of'),
    ({'username': 'x', 'password': 'short'}, f'at least {MIN_PASSWORD_LEN}'),
])
def test_create_user_rejects_bad_input(app, kwargs, message):
    with app.app_context():
        with pytest.raises(ValueError, match=message):
            create_user(**kwargs)


def test_create_user_rejects_duplicates(app):
    name = _name()
    with app.app_context():
        create_user(name, role='viewer')
        with pytest.raises(ValueError, match='already exists'):
            create_user(name, role='viewer')
    _cleanup(app, name)


def test_delete_user_removes_account_and_reports_missing(app, client):
    name = _name()
    with app.app_context():
        _, password = create_user(name, must_change_password=False)
        assert delete_user(name) is True
        assert delete_user(name) is False
    assert _login(client, name, password).status_code == 401


def test_delete_with_purge_anonymizes_audit_entries(app):
    name = _name()
    with app.app_context():
        user, _ = create_user(name)
        db.session.add(AuditLog(action='LOGIN_SUCCESS', username=name, user_id=user.id,
                                ip_address='203.0.113.9', details={}))
        db.session.commit()
        uid = user.id
        delete_user(name, purge=True)
        assert db.session.query(AuditLog).filter_by(username=name).count() == 0
        anonymized = db.session.query(AuditLog).filter_by(username=f'[deleted:{uid[:8]}]').all()
        assert anonymized and all(r.user_id is None and r.ip_address is None for r in anonymized)


# ── CLI ───────────────────────────────────────────────────────────────────────


def test_cli_create_with_generated_password_prints_it_once(app, client, runner):
    name = _name()
    result = runner.invoke(cli_module.cli, ['user', 'create', name, '--generate-password', '--no-force-change'])
    try:
        assert result.exit_code == 0, result.output
        password = result.stdout.strip().splitlines()[-1]
        assert len(password) >= 20
        assert password not in result.stderr          # the secret goes to stdout only
        assert _login(client, name, password).status_code == 200
    finally:
        _cleanup(app, name)


def test_cli_create_json_output(app, client, runner):
    name = _name()
    result = runner.invoke(cli_module.cli, ['user', 'create', name, '--role', 'admin',
                                            '--generate-password', '--no-force-change', '--json'])
    try:
        assert result.exit_code == 0, result.output
        data = json.loads(result.stdout)
        assert data['username'] == name
        assert _login(client, name, data['password']).status_code == 200
    finally:
        _cleanup(app, name)


def test_cli_prompts_for_password_and_never_echoes_it(app, client, runner):
    name = _name()
    secret = 'prompted-pass-1234'
    result = runner.invoke(cli_module.cli, ['user', 'create', name, '--no-force-change'],
                           input=f'{secret}\n{secret}\n')
    try:
        assert result.exit_code == 0, result.output
        assert secret not in result.stdout
        assert secret not in result.stderr
        assert _login(client, name, secret).status_code == 200
    finally:
        _cleanup(app, name)


def test_cli_has_no_password_argument():
    """A password on argv would end up in shell history and the process list."""
    cmd = cli_module.user_create
    assert not any('password' == p.name for p in cmd.params)
    assert not any(opt in ('--password', '-p') for p in cmd.params for opt in p.opts)


def test_cli_duplicate_user_fails(app, runner):
    name = _name()
    first = runner.invoke(cli_module.cli, ['user', 'create', name, '--generate-password'])
    second = runner.invoke(cli_module.cli, ['user', 'create', name, '--generate-password'])
    try:
        assert first.exit_code == 0
        assert second.exit_code == 1
        assert 'already exists' in second.stderr
    finally:
        _cleanup(app, name)


def test_cli_delete_user(app, runner):
    name = _name()
    runner.invoke(cli_module.cli, ['user', 'create', name, '--generate-password'])
    result = runner.invoke(cli_module.cli, ['user', 'delete', name, '--yes'])
    assert result.exit_code == 0
    again = runner.invoke(cli_module.cli, ['user', 'delete', name, '--yes'])
    assert again.exit_code == 1


def test_seed_rejects_a_plaintext_password_in_the_env(monkeypatch):
    monkeypatch.setenv('FLOWFORGE_PASSWORD', 'definitely-not-a-hash')
    result = CliRunner().invoke(cli_module.cli, ['db', 'seed'])
    assert result.exit_code == 1
    assert 'bcrypt hash' in result.stderr
    assert 'definitely-not-a-hash' not in result.output


def test_seed_skips_when_users_already_exist(app, runner, monkeypatch):
    monkeypatch.delenv('FLOWFORGE_PASSWORD', raising=False)
    result = runner.invoke(cli_module.cli, ['db', 'seed'])
    assert result.exit_code == 0
    assert 'already exists' in result.output
    with app.app_context():
        assert db.session.query(User).count() >= 1
