"""Tests for MFA (TOTP) endpoints — enroll, confirm, disable, verify, use-backup."""
from unittest.mock import MagicMock, patch


# ── /auth/mfa/status ──────────────────────────────────────────────────────────

def test_mfa_status_requires_auth(client):
    assert client.get('/api/auth/mfa/status').status_code == 401


def test_mfa_status_returns_enabled_false_by_default(client, headers):
    resp = client.get('/api/auth/mfa/status', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'mfa_enabled' in data
    assert data['mfa_enabled'] is False


# ── /auth/mfa/enroll ──────────────────────────────────────────────────────────

def test_mfa_enroll_requires_auth(client):
    assert client.post('/api/auth/mfa/enroll').status_code == 401


def test_mfa_enroll_pyotp_missing(client, headers):
    import sys
    original = sys.modules.get('pyotp', MagicMock())
    sys.modules['pyotp'] = None  # type: ignore[assignment]
    try:
        resp = client.post('/api/auth/mfa/enroll', headers=headers)
    finally:
        sys.modules['pyotp'] = original
    assert resp.status_code == 501
    assert 'pyotp' in resp.get_json()['error']


def test_mfa_enroll_returns_uri_and_secret(client, headers):
    mock_pyotp = MagicMock()
    mock_pyotp.random_base32.return_value = 'JBSWY3DPEHPK3PXP'
    totp_inst = MagicMock()
    totp_inst.provisioning_uri.return_value = 'otpauth://totp/FlowForge:testadmin?secret=JBSWY3DPEHPK3PXP'
    mock_pyotp.TOTP.return_value = totp_inst

    with patch.dict('sys.modules', {'pyotp': mock_pyotp}):
        resp = client.post('/api/auth/mfa/enroll', headers=headers)

    assert resp.status_code == 200
    data = resp.get_json()
    assert 'provisioning_uri' in data
    assert 'secret' in data


# ── /auth/mfa/confirm ─────────────────────────────────────────────────────────

def test_mfa_confirm_requires_auth(client):
    assert client.post('/api/auth/mfa/confirm', json={'code': '123456'}).status_code == 401


def test_mfa_confirm_pyotp_missing(client, headers):
    import sys
    original = sys.modules.get('pyotp', MagicMock())
    sys.modules['pyotp'] = None  # type: ignore[assignment]
    try:
        resp = client.post('/api/auth/mfa/confirm', json={'code': '123456'}, headers=headers)
    finally:
        sys.modules['pyotp'] = original
    assert resp.status_code == 501


def test_mfa_confirm_no_secret_enrolled(client, headers):
    # testadmin has no mfa_secret unless enroll was called; this tests that branch
    mock_pyotp = MagicMock()
    with patch.dict('sys.modules', {'pyotp': mock_pyotp}):
        # Reset mfa_secret to None first via disable (which is safe even without MFA enabled)
        client.post('/api/auth/mfa/disable', json={'password': 'testpass'}, headers=headers)
        resp = client.post('/api/auth/mfa/confirm', json={'code': '123456'}, headers=headers)
    assert resp.status_code == 400
    assert 'enroll' in resp.get_json()['error'].lower()


def test_mfa_confirm_missing_code(client, headers):
    mock_pyotp = MagicMock()
    mock_pyotp.random_base32.return_value = 'TESTSECRET32BASE'
    totp_inst = MagicMock()
    totp_inst.provisioning_uri.return_value = 'otpauth://...'
    mock_pyotp.TOTP.return_value = totp_inst

    with patch.dict('sys.modules', {'pyotp': mock_pyotp}):
        client.post('/api/auth/mfa/enroll', headers=headers)
        resp = client.post('/api/auth/mfa/confirm', json={}, headers=headers)
    assert resp.status_code == 400
    assert 'code' in resp.get_json()['error'].lower()


def test_mfa_confirm_invalid_code(client, headers):
    mock_pyotp = MagicMock()
    mock_pyotp.random_base32.return_value = 'TESTSECRETBASE32'
    totp_inst = MagicMock()
    totp_inst.provisioning_uri.return_value = 'otpauth://...'
    totp_inst.verify.return_value = False
    mock_pyotp.TOTP.return_value = totp_inst

    with patch.dict('sys.modules', {'pyotp': mock_pyotp}):
        client.post('/api/auth/mfa/enroll', headers=headers)
        resp = client.post('/api/auth/mfa/confirm', json={'code': '000000'}, headers=headers)
    assert resp.status_code == 400
    assert 'invalid' in resp.get_json()['error'].lower()


# ── /auth/mfa/disable ─────────────────────────────────────────────────────────

def test_mfa_disable_requires_auth(client):
    assert client.post('/api/auth/mfa/disable', json={'password': 'testpass'}).status_code == 401


def test_mfa_disable_missing_password(client, headers):
    resp = client.post('/api/auth/mfa/disable', json={}, headers=headers)
    assert resp.status_code == 400
    assert 'password' in resp.get_json()['error'].lower()


def test_mfa_disable_wrong_password(client, headers):
    resp = client.post('/api/auth/mfa/disable', json={'password': 'wrongpassword'}, headers=headers)
    assert resp.status_code == 401
    assert 'incorrect' in resp.get_json()['error'].lower()


def test_mfa_disable_correct_password(client, headers):
    resp = client.post('/api/auth/mfa/disable', json={'password': 'testpass'}, headers=headers)
    assert resp.status_code == 200
    assert 'disabled' in resp.get_json()['message'].lower()


# ── /auth/mfa/verify ──────────────────────────────────────────────────────────

def test_mfa_verify_pyotp_missing(client):
    import sys
    original = sys.modules.get('pyotp', MagicMock())
    sys.modules['pyotp'] = None  # type: ignore[assignment]
    try:
        resp = client.post('/api/auth/mfa/verify',
                           json={'mfa_token': 'tok', 'code': '123456'})
    finally:
        sys.modules['pyotp'] = original
    assert resp.status_code == 501


def test_mfa_verify_missing_fields(client):
    mock_pyotp = MagicMock()
    with patch.dict('sys.modules', {'pyotp': mock_pyotp}):
        resp = client.post('/api/auth/mfa/verify', json={})
    assert resp.status_code == 400
    assert 'required' in resp.get_json()['error'].lower()


def test_mfa_verify_invalid_mfa_token(client):
    mock_pyotp = MagicMock()
    with patch.dict('sys.modules', {'pyotp': mock_pyotp}):
        resp = client.post('/api/auth/mfa/verify',
                           json={'mfa_token': 'not.a.valid.token', 'code': '123456'})
    assert resp.status_code == 401
    assert 'invalid' in resp.get_json()['error'].lower()


def test_mfa_verify_valid_token_mfa_not_configured(app, client):
    """A valid MFA challenge token for a user without MFA returns 400."""
    with app.app_context():
        from flowforge.api.auth import generate_mfa_token
        from flowforge.db.models import User, db
        user = db.session.query(User).filter_by(username='testadmin').first()
        mfa_tok = generate_mfa_token(user)

    mock_pyotp = MagicMock()
    with patch.dict('sys.modules', {'pyotp': mock_pyotp}):
        resp = client.post('/api/auth/mfa/verify',
                           json={'mfa_token': mfa_tok, 'code': '123456'})
    assert resp.status_code == 400
    assert 'not configured' in resp.get_json()['error'].lower()


# ── /auth/mfa/use-backup ──────────────────────────────────────────────────────

def test_mfa_use_backup_missing_fields(client):
    resp = client.post('/api/auth/mfa/use-backup', json={})
    assert resp.status_code == 400
    assert 'required' in resp.get_json()['error'].lower()


def test_mfa_use_backup_invalid_mfa_token(client):
    resp = client.post('/api/auth/mfa/use-backup',
                       json={'mfa_token': 'not.valid', 'backup_code': 'ABCD-1234'})
    assert resp.status_code == 401
    assert 'invalid' in resp.get_json()['error'].lower()


def test_mfa_use_backup_mfa_not_configured(app, client):
    """Valid MFA token but user has MFA disabled → 400."""
    with app.app_context():
        from flowforge.api.auth import generate_mfa_token
        from flowforge.db.models import User, db
        user = db.session.query(User).filter_by(username='testadmin').first()
        mfa_tok = generate_mfa_token(user)

    resp = client.post('/api/auth/mfa/use-backup',
                       json={'mfa_token': mfa_tok, 'backup_code': 'ABCD-1234'})
    assert resp.status_code == 400
    assert 'not configured' in resp.get_json()['error'].lower()
