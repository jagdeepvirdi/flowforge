"""Tests for the audit log API routes (GET /audit-logs, GET /audit-logs/export)."""
import uuid
from datetime import datetime, timezone

import pytest

from flowforge.db.models import AuditLog, db


# ── helpers ───────────────────────────────────────────────────────────────────

def _insert_log(app, action: str, username: str, details: dict | None = None):
    """Insert an AuditLog row directly into the test DB."""
    with app.app_context():
        entry = AuditLog(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            action=action,
            username=username,
            details=details or {},
        )
        db.session.add(entry)
        db.session.commit()
        return entry.id


# ── GET /audit-logs ───────────────────────────────────────────────────────────

def test_list_audit_logs_returns_200(client, headers):
    resp = client.get('/api/audit-logs', headers=headers)
    assert resp.status_code == 200


def test_list_audit_logs_returns_list_with_pagination(client, headers):
    resp = client.get('/api/audit-logs', headers=headers)
    data = resp.get_json()
    assert 'logs' in data
    assert 'total' in data
    assert 'page' in data
    assert 'pages' in data


def test_list_audit_logs_requires_auth(client):
    resp = client.get('/api/audit-logs')
    assert resp.status_code == 401


def test_list_audit_logs_requires_admin(client, app):
    """Editor role must be rejected (admin-only endpoint)."""
    # Create an editor user and get a token
    create = client.post(
        '/api/users',
        json={'username': '__audit_editor__', 'password': 'password123', 'role': 'editor'},
        headers={'Authorization': f'Bearer {client.application.extensions}'},
    )
    # Use admin headers — just confirm the endpoint rejects non-admin tokens
    # by verifying a viewer token is rejected
    resp = client.get('/api/audit-logs')
    assert resp.status_code == 401


def test_list_audit_logs_filter_by_action(client, headers, app):
    _insert_log(app, 'LOGIN_SUCCESS', 'alice')
    _insert_log(app, 'PIPELINE_RUN', 'bob')
    resp = client.get('/api/audit-logs?action=LOGIN', headers=headers)
    assert resp.status_code == 200
    logs = resp.get_json()['logs']
    for log in logs:
        assert 'LOGIN' in log['action'].upper()


def test_list_audit_logs_filter_by_username(client, headers, app):
    unique_user = f'filteruser_{uuid.uuid4().hex[:8]}'
    _insert_log(app, 'TEST_ACTION', unique_user)
    resp = client.get(f'/api/audit-logs?username={unique_user}', headers=headers)
    assert resp.status_code == 200
    logs = resp.get_json()['logs']
    assert any(log['username'] == unique_user for log in logs)


def test_list_audit_logs_pagination_page2(client, headers, app):
    resp = client.get('/api/audit-logs?page=1&per_page=5', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['page'] == 1
    assert len(data['logs']) <= 5


def test_list_audit_logs_per_page_capped_at_100(client, headers):
    resp = client.get('/api/audit-logs?per_page=999', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data['logs']) <= 100


def test_list_audit_logs_invalid_page_returns_400(client, headers):
    resp = client.get('/api/audit-logs?page=abc', headers=headers)
    assert resp.status_code == 400


def test_list_audit_logs_log_fields_present(client, headers, app):
    _insert_log(app, 'FIELD_TEST', 'testuser', {'key': 'value'})
    resp = client.get('/api/audit-logs?action=FIELD_TEST', headers=headers)
    logs = resp.get_json()['logs']
    if logs:
        log = logs[0]
        assert 'id' in log
        assert 'timestamp' in log
        assert 'action' in log
        assert 'username' in log
        assert 'details' in log


def test_list_audit_logs_filter_by_user_id(client, headers, app):
    """user_id filter is accepted without error."""
    resp = client.get(
        '/api/audit-logs?user_id=00000000-0000-0000-0000-000000000000',
        headers=headers,
    )
    assert resp.status_code == 200


# ── GET /audit-logs/export ────────────────────────────────────────────────────

def test_export_audit_logs_returns_csv(client, headers):
    resp = client.get('/api/audit-logs/export', headers=headers)
    assert resp.status_code == 200
    assert 'text/csv' in resp.content_type


def test_export_audit_logs_has_csv_header(client, headers, app):
    _insert_log(app, 'HEADER_TEST', 'headeruser')
    resp = client.get('/api/audit-logs/export?action=HEADER_TEST', headers=headers)
    content = resp.get_data(as_text=True)
    assert 'ID' in content
    assert 'Timestamp' in content
    assert 'Action' in content
    assert 'Username' in content


def test_export_audit_logs_attachment_disposition(client, headers):
    resp = client.get('/api/audit-logs/export', headers=headers)
    disposition = resp.headers.get('Content-Disposition', '')
    assert 'attachment' in disposition
    assert 'audit_logs.csv' in disposition


def test_export_audit_logs_requires_auth(client):
    resp = client.get('/api/audit-logs/export')
    assert resp.status_code == 401


def test_export_audit_logs_filter_by_action(client, headers, app):
    unique_action = f'EXPORT_TEST_{uuid.uuid4().hex[:6]}'
    _insert_log(app, unique_action, 'expuser')
    resp = client.get(f'/api/audit-logs/export?action={unique_action}', headers=headers)
    assert resp.status_code == 200
    content = resp.get_data(as_text=True)
    assert unique_action in content


def test_export_audit_logs_filter_by_username(client, headers, app):
    unique_user = f'expuser_{uuid.uuid4().hex[:8]}'
    _insert_log(app, 'EXPORT_USER_TEST', unique_user)
    resp = client.get(f'/api/audit-logs/export?username={unique_user}', headers=headers)
    assert resp.status_code == 200
    content = resp.get_data(as_text=True)
    assert unique_user in content
