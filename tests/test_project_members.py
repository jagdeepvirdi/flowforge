"""Tests for team-scoped project access — ff_project_members enforcement."""
import pytest

from flowforge.db.models import DEFAULT_PROJECT_ID


@pytest.fixture
def other_project(client, headers):
    """A second, non-default project that test users are NOT members of by default."""
    resp = client.post('/api/projects', json={'name': 'Isolated Project'}, headers=headers)
    assert resp.status_code == 201
    pid = resp.get_json()['id']
    yield pid
    client.delete(f'/api/projects/{pid}', headers=headers)


@pytest.fixture
def member_user(client, headers):
    """A non-admin editor user. New users auto-get Default project membership."""
    resp = client.post('/api/users', json={
        'username': 'pm_editor_test', 'password': 'Pass1234!', 'role': 'editor',
    }, headers=headers)
    assert resp.status_code == 201
    user_id = resp.get_json()['id']
    login = client.post('/api/auth/login', json={'username': 'pm_editor_test', 'password': 'Pass1234!'})
    token = login.get_json()['token']
    member_headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    yield user_id, member_headers
    client.delete(f'/api/users/{user_id}', headers=headers)


# ── auto-membership ────────────────────────────────────────────────────────────

def test_new_user_auto_added_to_default_project(client, headers, member_user):
    user_id, _ = member_user
    resp = client.get(f'/api/projects/{DEFAULT_PROJECT_ID}/members', headers=headers)
    assert resp.status_code == 200
    member_ids = {m['user_id'] for m in resp.get_json()}
    assert user_id in member_ids


def test_new_admin_user_not_added_as_member_row(client, headers):
    """Admins bypass the check everywhere, so they don't need a membership row."""
    resp = client.post('/api/users', json={
        'username': 'pm_admin_test', 'password': 'Pass1234!', 'role': 'admin',
    }, headers=headers)
    assert resp.status_code == 201
    user_id = resp.get_json()['id']
    try:
        members = client.get(f'/api/projects/{DEFAULT_PROJECT_ID}/members', headers=headers).get_json()
        assert user_id not in {m['user_id'] for m in members}
    finally:
        client.delete(f'/api/users/{user_id}', headers=headers)


def test_project_creator_auto_added_as_member(client, headers, member_user):
    _, member_headers = member_user
    resp = client.post('/api/projects', json={'name': 'Creator Auto-Membership'}, headers=member_headers)
    assert resp.status_code == 201
    pid = resp.get_json()['id']
    try:
        # The creator must be able to see their own project immediately
        get_resp = client.get(f'/api/projects/{pid}', headers=member_headers)
        assert get_resp.status_code == 200
    finally:
        client.delete(f'/api/projects/{pid}', headers=headers)


# ── enforcement — a member (non-admin) can use the Default project ────────────

def test_member_can_list_default_project_pipelines(client, headers, member_user):
    _, member_headers = member_user
    resp = client.get('/api/pipelines', headers=member_headers)
    assert resp.status_code == 200


def test_member_can_create_pipeline_in_default_project(client, headers, member_user):
    _, member_headers = member_user
    resp = client.post('/api/pipelines', json={'name': 'member pipeline'}, headers=member_headers)
    assert resp.status_code == 201
    pid = resp.get_json()['id']
    client.delete(f'/api/pipelines/{pid}', headers=headers)


# ── enforcement — denied access to a project the user isn't a member of ───────

def test_non_member_denied_get_project(client, headers, member_user, other_project):
    _, member_headers = member_user
    resp = client.get(f'/api/projects/{other_project}', headers=member_headers)
    assert resp.status_code == 403


def test_non_member_denied_creating_pipeline_in_other_project(client, headers, member_user, other_project):
    _, member_headers = member_user
    resp = client.post('/api/pipelines',
                       json={'name': 'sneaky pipeline', 'project_id': other_project},
                       headers=member_headers)
    assert resp.status_code == 403


def test_non_member_denied_get_pipeline_in_other_project(client, headers, member_user, other_project):
    _, member_headers = member_user
    created = client.post('/api/pipelines',
                          json={'name': 'admin-owned pipeline', 'project_id': other_project},
                          headers=headers).get_json()
    try:
        resp = client.get(f'/api/pipelines/{created["id"]}', headers=member_headers)
        assert resp.status_code == 403
    finally:
        client.delete(f'/api/pipelines/{created["id"]}', headers=headers)


def test_non_member_denied_creating_report_in_other_project(client, headers, member_user, other_project):
    _, member_headers = member_user
    resp = client.post('/api/report-configs',
                       json={'name': 'sneaky report', 'query': 'SELECT 1', 'format': 'csv',
                             'output_filename': 'r.csv', 'project_id': other_project},
                       headers=member_headers)
    assert resp.status_code == 403


def test_non_member_denied_creating_email_in_other_project(client, headers, member_user, other_project):
    _, member_headers = member_user
    resp = client.post('/api/email-configs',
                       json={'name': 'sneaky email', 'subject': 'x', 'body_template': 'x',
                             'project_id': other_project},
                       headers=member_headers)
    assert resp.status_code == 403


def test_non_member_denied_creating_recipient_group_in_other_project(client, headers, member_user, other_project):
    _, member_headers = member_user
    resp = client.post('/api/recipient-groups',
                       json={'name': 'sneaky group', 'addresses': ['x@x.com'], 'project_id': other_project},
                       headers=member_headers)
    assert resp.status_code == 403


def test_non_member_unfiltered_pipeline_list_excludes_other_project(client, headers, member_user, other_project):
    """Unlike an admin (test_pipelines_unfiltered_returns_all), a non-admin's
    unfiltered list is scoped to only the projects they're a member of."""
    _, member_headers = member_user
    created = client.post('/api/pipelines',
                          json={'name': 'admin-only pipeline', 'project_id': other_project},
                          headers=headers).get_json()
    try:
        visible = client.get('/api/pipelines', headers=member_headers).get_json()
        assert created['id'] not in {p['id'] for p in visible}
    finally:
        client.delete(f'/api/pipelines/{created["id"]}', headers=headers)


def test_non_member_project_excluded_from_list_projects(client, headers, member_user, other_project):
    _, member_headers = member_user
    visible = client.get('/api/projects', headers=member_headers).get_json()
    assert other_project not in {p['id'] for p in visible}


# ── membership after being explicitly added ────────────────────────────────────

def test_member_granted_access_after_being_added(client, headers, member_user, other_project):
    user_id, member_headers = member_user
    add_resp = client.post(f'/api/projects/{other_project}/members', json={'user_id': user_id}, headers=headers)
    assert add_resp.status_code == 201

    resp = client.get(f'/api/projects/{other_project}', headers=member_headers)
    assert resp.status_code == 200


def test_member_loses_access_after_being_removed(client, headers, member_user, other_project):
    user_id, member_headers = member_user
    client.post(f'/api/projects/{other_project}/members', json={'user_id': user_id}, headers=headers)
    assert client.get(f'/api/projects/{other_project}', headers=member_headers).status_code == 200

    remove_resp = client.delete(f'/api/projects/{other_project}/members/{user_id}', headers=headers)
    assert remove_resp.status_code == 200
    assert client.get(f'/api/projects/{other_project}', headers=member_headers).status_code == 403


# ── membership management endpoints ────────────────────────────────────────────

def test_add_member_requires_admin(client, headers, member_user, other_project):
    """A non-admin member of a project cannot add other members (admin-only)."""
    user_id, member_headers = member_user
    client.post(f'/api/projects/{other_project}/members', json={'user_id': user_id}, headers=headers)
    resp = client.post(f'/api/projects/{other_project}/members', json={'user_id': user_id}, headers=member_headers)
    assert resp.status_code == 403


def test_add_duplicate_member_returns_409(client, headers, member_user, other_project):
    user_id, _ = member_user
    r1 = client.post(f'/api/projects/{other_project}/members', json={'user_id': user_id}, headers=headers)
    assert r1.status_code == 201
    r2 = client.post(f'/api/projects/{other_project}/members', json={'user_id': user_id}, headers=headers)
    assert r2.status_code == 409


def test_add_member_missing_user_id_returns_400(client, headers, other_project):
    resp = client.post(f'/api/projects/{other_project}/members', json={}, headers=headers)
    assert resp.status_code == 400


def test_add_member_nonexistent_user_returns_404(client, headers, other_project):
    resp = client.post(
        f'/api/projects/{other_project}/members',
        json={'user_id': '00000000-0000-0000-0000-000000000099'},
        headers=headers,
    )
    assert resp.status_code == 404


def test_remove_nonexistent_membership_returns_404(client, headers, other_project):
    resp = client.delete(
        f'/api/projects/{other_project}/members/00000000-0000-0000-0000-000000000099',
        headers=headers,
    )
    assert resp.status_code == 404


def test_list_members_requires_project_access(client, headers, member_user, other_project):
    _, member_headers = member_user
    resp = client.get(f'/api/projects/{other_project}/members', headers=member_headers)
    assert resp.status_code == 403


def test_member_can_view_own_project_member_list(client, headers, member_user, other_project):
    user_id, member_headers = member_user
    client.post(f'/api/projects/{other_project}/members', json={'user_id': user_id}, headers=headers)
    resp = client.get(f'/api/projects/{other_project}/members', headers=member_headers)
    assert resp.status_code == 200
    assert any(m['user_id'] == user_id for m in resp.get_json())


def test_member_dict_includes_username_and_role(client, headers, member_user, other_project):
    user_id, _ = member_user
    client.post(f'/api/projects/{other_project}/members', json={'user_id': user_id}, headers=headers)
    members = client.get(f'/api/projects/{other_project}/members', headers=headers).get_json()
    entry = next(m for m in members if m['user_id'] == user_id)
    assert entry['username'] == 'pm_editor_test'
    assert entry['role'] == 'editor'
