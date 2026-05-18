"""
Manual smoke test: verify the APScheduler triggers pipelines on schedule.

Creates a pipeline with a 1-minute cron schedule, waits up to 90 seconds for
a run to appear in history, then cleans up.

Usage:
    python tests/manual/check_scheduler.py [--url URL] [--user USER] [--pass PASS]
"""
import argparse
import json
import sys
import time
import urllib.request
import urllib.error


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


def create_scheduled_pipeline(base, token):
    """Create a pipeline that runs every minute (cron: * * * * *)."""
    status, pipeline = _request('POST', f'{base}/api/pipelines', {
        'name': '_smoke_scheduler_test',
        'description': 'Temporary pipeline for scheduler smoke test',
        'schedule': '* * * * *',
        'enabled': True,
    }, token)
    if status != 201:
        print(f'[FAIL] Create pipeline failed ({status}): {pipeline}')
        sys.exit(1)
    pid = pipeline['id']
    print(f'[OK]   Created pipeline {pid} with schedule "* * * * *"')
    return pid


def wait_for_scheduled_run(base, token, pipeline_id, timeout=90):
    """Poll /api/runs until a run for this pipeline appears."""
    print(f'       Waiting up to {timeout}s for scheduler to trigger a run...')
    deadline = time.time() + timeout
    while time.time() < deadline:
        status, runs = _request('GET', f'{base}/api/runs?limit=20', token=token)
        if status == 200:
            matching = [r for r in runs if r.get('pipeline_id') == pipeline_id]
            if matching:
                run = matching[0]
                print(f'[OK]   Scheduler triggered run {run["id"]} (status: {run["status"]})')
                return run
        remaining = int(deadline - time.time())
        print(f'       No run yet — {remaining}s remaining...')
        time.sleep(5)
    return None


def disable_and_delete(base, token, pipeline_id):
    # Disable first to stop further scheduled runs
    _request('PUT', f'{base}/api/pipelines/{pipeline_id}',
             {'enabled': False}, token)
    status, _ = _request('DELETE', f'{base}/api/pipelines/{pipeline_id}', token=token)
    if status == 200:
        print(f'[OK]   Deleted pipeline {pipeline_id}')
    else:
        print(f'[WARN] Could not delete pipeline {pipeline_id}')


def main():
    parser = argparse.ArgumentParser(description='FlowForge scheduler smoke test')
    parser.add_argument('--url', default='http://localhost:5000')
    parser.add_argument('--user', default='admin')
    parser.add_argument('--pass', dest='password', default='admin')
    parser.add_argument('--timeout', type=int, default=90,
                        help='Max seconds to wait for a scheduled run (default 90)')
    args = parser.parse_args()

    base = args.url.rstrip('/')
    token = login(base, args.user, args.password)
    pipeline_id = create_scheduled_pipeline(base, token)

    try:
        run = wait_for_scheduled_run(base, token, pipeline_id, timeout=args.timeout)
        if run:
            print(f'[PASS] Scheduler test passed — run triggered automatically')
            print(f'       Triggered by: {run.get("triggered_by")}')
            print(f'       Status:       {run.get("status")}')
        else:
            print(f'[FAIL] No scheduled run appeared within {args.timeout}s')
            print('       Check that the scheduler is running (server_start.ps1 or server_start.sh)')
            sys.exit(1)
    finally:
        disable_and_delete(base, token, pipeline_id)


if __name__ == '__main__':
    main()
