#!/usr/bin/env python
"""
Manual end-to-end API smoke test.
Runs against the live FlowForge server.

Usage:
    python tests/manual/check_api.py
    python tests/manual/check_api.py --url http://localhost:5000 --user admin --pass <your-password>
"""
import argparse
import os
import sys
import json
import urllib.request
import urllib.error

GREEN = '\033[92m'
RED   = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'
BOLD  = '\033[1m'

passed = 0
failed = 0


def ok(label):
    global passed
    passed += 1
    print(f'  {GREEN}✓{RESET} {label}')


def fail(label, reason=''):
    global failed
    failed += 1
    msg = f': {reason}' if reason else ''
    print(f'  {RED}✗{RESET} {label}{msg}')


def request(method, url, data=None, token=None):
    body = json.dumps(data).encode() if data is not None else None
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {}
    except Exception as e:
        return 0, {'error': str(e)}


def section(title):
    print(f'\n{BOLD}{title}{RESET}')


def run(base_url, username, password):
    token = None

    # ── Health ────────────────────────────────────────────────────────────────
    section('Health check')
    status, data = request('GET', f'{base_url}/api/health')
    if status == 200 and data.get('status') == 'ok':
        ok('GET /api/health')
    else:
        fail('GET /api/health', f'status={status}')

    # ── Auth ──────────────────────────────────────────────────────────────────
    section('Auth')
    status, data = request('POST', f'{base_url}/api/auth/login',
                           {'username': username, 'password': password})
    if status == 200 and 'token' in data:
        ok(f'Login as {username!r}')
        token = data['token']
    else:
        fail(f'Login as {username!r}', f'status={status} {data.get("error","")}')
        print(f'\n{RED}Cannot continue without a valid token.{RESET}')
        return

    status, _ = request('POST', f'{base_url}/api/auth/login',
                         {'username': 'nobody', 'password': 'bad'})
    if status == 401:
        ok('Reject bad credentials (401)')
    else:
        fail('Reject bad credentials', f'got {status}')

    status, _ = request('GET', f'{base_url}/api/pipelines')
    if status == 401:
        ok('Protected route without token (401)')
    else:
        fail('Protected route without token', f'got {status}')

    # ── DB Connection CRUD ────────────────────────────────────────────────────
    section('DB Connections')
    status, data = request('GET', f'{base_url}/api/db-connections', token=token)
    if status == 200:
        ok(f'List connections ({len(data)} found)')
    else:
        fail('List connections', f'status={status}')

    conn_payload = {
        'name': '[smoke-test] FlowForge DB',
        'db_type': 'postgresql',
        'config': {'host': 'localhost', 'port': 5434, 'database': 'flowforge',
                   'username': 'flowforge', 'password': os.environ.get('DB_PASSWORD', '')},
    }
    status, data = request('POST', f'{base_url}/api/db-connections', conn_payload, token)
    if status == 201:
        ok('Create connection')
        conn_id = data['id']
    else:
        fail('Create connection', f'status={status} {data.get("error","")}')
        conn_id = None

    if conn_id:
        status, data = request('POST', f'{base_url}/api/db-connections/test-raw', {
            'db_type': 'postgresql',
            'config': {'host': 'localhost', 'port': 5434, 'database': 'flowforge',
                       'username': 'flowforge', 'password': os.environ.get('DB_PASSWORD', '')},
        }, token)
        if status == 200 and data.get('success'):
            ok(f'Test-raw connection ({data.get("latency_ms")}ms)')
        else:
            fail('Test-raw connection', data.get('error', ''))

        status, data = request('POST', f'{base_url}/api/db-connections/{conn_id}/test', token=token)
        if status == 200 and data.get('success'):
            ok(f'Test saved connection ({data.get("latency_ms")}ms)')
        else:
            fail('Test saved connection', data.get('error', ''))

    # ── Pipelines CRUD ────────────────────────────────────────────────────────
    section('Pipelines')
    status, data = request('GET', f'{base_url}/api/pipelines', token=token)
    if status == 200:
        ok(f'List pipelines ({len(data)} found)')
    else:
        fail('List pipelines', f'status={status}')

    pip_payload = {'name': '[smoke-test] Pipeline', 'enabled': True}
    status, data = request('POST', f'{base_url}/api/pipelines', pip_payload, token)
    if status == 201:
        ok('Create pipeline')
        pip_id = data['id']
    else:
        fail('Create pipeline', f'status={status} {data.get("error","")}')
        pip_id = None

    if pip_id:
        status, _ = request('PUT', f'{base_url}/api/pipelines/{pip_id}',
                             {'name': '[smoke-test] Renamed'}, token)
        ok('Update pipeline') if status == 200 else fail('Update pipeline', f'status={status}')

    # ── Report Configs ────────────────────────────────────────────────────────
    section('Report Configs')
    rep_payload = {
        'name': '[smoke-test] Report',
        'query': 'SELECT 1 AS n',
        'format': 'csv',
        'output_filename': 'test_{{ current_date }}.csv',
        'connection_id': conn_id,
    }
    status, data = request('POST', f'{base_url}/api/report-configs', rep_payload, token)
    if status == 201:
        ok('Create report config')
        rep_id = data['id']
    else:
        fail('Create report config', f'status={status} {data.get("error","")}')
        rep_id = None

    if rep_id and conn_id:
        status, data = request('POST', f'{base_url}/api/report-configs/{rep_id}/preview', token=token)
        if status == 200 and 'rows' in data:
            ok(f'Preview report ({len(data["rows"])} rows)')
        else:
            fail('Preview report', data.get('error', f'status={status}'))

    # ── Recipients ────────────────────────────────────────────────────────────
    section('Recipient Groups')
    grp_payload = {'name': '[smoke-test] Group', 'addresses': ['test@example.com']}
    status, data = request('POST', f'{base_url}/api/recipient-groups', grp_payload, token)
    if status == 201:
        ok('Create recipient group')
        grp_id = data['id']
    else:
        fail('Create recipient group', f'status={status} {data.get("error","")}')
        grp_id = None

    # ── Run History ───────────────────────────────────────────────────────────
    section('Run History')
    status, data = request('GET', f'{base_url}/api/runs', token=token)
    if status == 200:
        ok(f'List runs ({len(data)} found)')
    else:
        fail('List runs', f'status={status}')

    # ── Cleanup ───────────────────────────────────────────────────────────────
    section('Cleanup smoke-test data')
    for path, label in [
        (f'/api/report-configs/{rep_id}' if rep_id else None, 'report config'),
        (f'/api/pipelines/{pip_id}' if pip_id else None, 'pipeline'),
        (f'/api/db-connections/{conn_id}' if conn_id else None, 'db connection'),
        (f'/api/recipient-groups/{grp_id}' if grp_id else None, 'recipient group'),
    ]:
        if path:
            status, _ = request('DELETE', f'{base_url}{path}', token=token)
            ok(f'Deleted {label}') if status == 200 else fail(f'Delete {label}', f'status={status}')

    # ── Summary ───────────────────────────────────────────────────────────────
    total = passed + failed
    print(f'\n{"─"*40}')
    print(f'{BOLD}Results: {GREEN}{passed}{RESET}{BOLD} passed, {RED}{failed}{RESET}{BOLD} failed / {total} total{RESET}')
    print('─'*40)
    return failed == 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='FlowForge API smoke test')
    parser.add_argument('--url',  default='http://localhost:5000', help='Base URL of the API')
    parser.add_argument('--user', default='admin',     help='Username')
    parser.add_argument('--pass', dest='password', default=os.environ.get('FLOWFORGE_PASSWORD', ''), help='Password (or set FLOWFORGE_PASSWORD env var)')
    args = parser.parse_args()

    success = run(args.url, args.user, args.password)
    sys.exit(0 if success else 1)
