"""
Manual smoke test: trigger a real pipeline run via API and poll until complete.

Usage:
    python tests/manual/check_runner.py [--url URL] [--user USER] [--pass PASS] [--pipeline PIPELINE_ID]

If --pipeline is omitted, the script creates a minimal test pipeline, runs it,
verifies the run record, then deletes it.
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def _request(method, url, data=None, token=None):
    body = json.dumps(data).encode() if data else None
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def login(base, username, password):
    status, data = _request('POST', f'{base}/api/auth/login',
                             {'username': username, 'password': password})
    if status != 200:
        print(f'[FAIL] Login failed ({status}): {data}')
        sys.exit(1)
    print('[OK]   Logged in')
    return data['token']


def create_test_pipeline(base, token):
    """Create a minimal pipeline with a single db_query step (SELECT 1)."""
    status, pipeline = _request('POST', f'{base}/api/pipelines', {
        'name': '_smoke_test_pipeline',
        'description': 'Temporary pipeline for runner smoke test',
        'enabled': True,
    }, token)
    assert status == 201, f'Create pipeline failed: {pipeline}'
    pid = pipeline['id']
    print(f'[OK]   Created pipeline {pid}')

    # Add a step that just runs SELECT 1 using the default env-var connection
    status, step = _request('POST', f'{base}/api/pipelines/{pid}/steps', {
        'name': 'smoke_query',
        'step_type': 'db_query',
        'step_order': 1,
        'config': {'query': 'SELECT 1', 'connection_id': None},
        'on_error': 'stop',
        'enabled': True,
    }, token)
    if status != 201:
        print(f'[WARN] Step creation failed ({status}): {step}')

    return pid


def trigger_run(base, token, pipeline_id):
    status, data = _request('POST', f'{base}/api/pipelines/{pipeline_id}/run', {}, token)
    if status not in (200, 201, 202):
        print(f'[FAIL] Trigger run failed ({status}): {data}')
        sys.exit(1)
    run_id = data.get('run_id') or data.get('id')
    print(f'[OK]   Triggered run {run_id}')
    return run_id


def poll_run(base, token, run_id, timeout=60):
    """Poll /api/runs/{run_id} until status is success or failed."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        status, data = _request('GET', f'{base}/api/runs/{run_id}', token=token)
        if status != 200:
            print(f'[FAIL] Could not fetch run {run_id}: {status}')
            sys.exit(1)
        run_status = data.get('status')
        print(f'       Run status: {run_status}')
        if run_status in ('success', 'failed', 'cancelled'):
            return run_status, data
        time.sleep(2)
    print(f'[FAIL] Run did not complete within {timeout}s')
    sys.exit(1)


def delete_pipeline(base, token, pipeline_id):
    status, _ = _request('DELETE', f'{base}/api/pipelines/{pipeline_id}', token=token)
    if status == 200:
        print(f'[OK]   Deleted pipeline {pipeline_id}')
    else:
        print(f'[WARN] Could not delete pipeline {pipeline_id} (status {status})')


def main():
    parser = argparse.ArgumentParser(description='FlowForge runner smoke test')
    parser.add_argument('--url', default='http://localhost:5000', help='API base URL')
    parser.add_argument('--user', default='admin', help='Username')
    parser.add_argument('--pass', dest='password', default='admin', help='Password')
    parser.add_argument('--pipeline', default=None, help='Existing pipeline ID to run (optional)')
    parser.add_argument('--timeout', type=int, default=60, help='Max seconds to wait for run')
    args = parser.parse_args()

    base = args.url.rstrip('/')
    created_pipeline = None

    token = login(base, args.user, args.password)

    pipeline_id = args.pipeline
    if not pipeline_id:
        pipeline_id = create_test_pipeline(base, token)
        created_pipeline = pipeline_id

    try:
        run_id = trigger_run(base, token, pipeline_id)
        final_status, run_data = poll_run(base, token, run_id, timeout=args.timeout)

        if final_status == 'success':
            print('[PASS] Pipeline run completed successfully')
            print(f'       Duration: {run_data.get("duration_ms")}ms')
        else:
            print(f'[FAIL] Pipeline run ended with status: {final_status}')
            print(f'       Error: {run_data.get("error_message")}')
            sys.exit(1)

    finally:
        if created_pipeline:
            delete_pipeline(base, token, created_pipeline)


if __name__ == '__main__':
    main()
