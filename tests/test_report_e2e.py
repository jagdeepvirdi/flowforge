"""E2E tests: SQL → ReportStep → file on disk.

Each test runs the full chain:
  real PostgreSQL (test DB) → ReportStep.run() → assert file exists with correct content.

Requires FLOWFORGE_DB_URL pointing to a database whose name contains "test".
"""
import csv
import os
import uuid
import pytest

SEED_QUERY = (
    "SELECT 1 AS id, 'Alice' AS name, 1200.50 AS amount "
    "UNION ALL SELECT 2, 'Bob', 980.00 "
    "UNION ALL SELECT 3, 'Carol', 2450.75 "
    "ORDER BY id"
)


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def report_conn_id(client, headers, live_db_config):
    """A live DB connection pointing at the test database."""
    resp = client.post('/api/db-connections', json={
        'name': f'E2E Report DB {uuid.uuid4().hex[:6]}',
        'db_type': 'postgresql',
        'config': live_db_config,
    }, headers=headers)
    assert resp.status_code == 201, resp.get_json()
    cid = resp.get_json()['id']
    yield cid
    client.delete(f'/api/db-connections/{cid}', headers=headers)


@pytest.fixture
def csv_report_id(client, headers, report_conn_id):
    """A CSV ReportConfig that runs the seed query."""
    resp = client.post('/api/report-configs', json={
        'name': f'E2E CSV {uuid.uuid4().hex[:6]}',
        'connection_id': report_conn_id,
        'query': SEED_QUERY,
        'format': 'csv',
        'output_filename': 'e2e_test.csv',
    }, headers=headers)
    assert resp.status_code == 201, resp.get_json()
    rid = resp.get_json()['id']
    yield rid
    client.delete(f'/api/report-configs/{rid}', headers=headers)


@pytest.fixture
def excel_report_id(client, headers, report_conn_id):
    """An Excel ReportConfig with a custom sheet name."""
    resp = client.post('/api/report-configs', json={
        'name': f'E2E Excel {uuid.uuid4().hex[:6]}',
        'connection_id': report_conn_id,
        'query': SEED_QUERY,
        'format': 'excel',
        'output_filename': 'e2e_test.xlsx',
        'sheet_name': 'TestSheet',
    }, headers=headers)
    assert resp.status_code == 201, resp.get_json()
    rid = resp.get_json()['id']
    yield rid
    client.delete(f'/api/report-configs/{rid}', headers=headers)


def _run_report_step(app, report_config_id: str, tmp_path):
    """Instantiate ReportStep, monkeypatch output dir, run inside app context."""
    from flowforge.steps.report import ReportStep
    from flowforge.engine.context import build

    os.environ['FLOWFORGE_OUTPUT_DIR'] = str(tmp_path)
    try:
        with app.app_context():
            step = ReportStep(name='e2e_report', config={'report_config_id': report_config_id})
            context = build('E2E Pipeline')
            return step.run(context)
    finally:
        del os.environ['FLOWFORGE_OUTPUT_DIR']


# ── tests ─────────────────────────────────────────────────────────────────────

def test_report_e2e_csv(app, csv_report_id, tmp_path):
    result = _run_report_step(app, csv_report_id, tmp_path)

    assert result.success, f"Step failed: {result.error}"
    assert result.rows_affected == 3

    out = tmp_path / 'e2e_test.csv'
    assert out.exists()
    assert out.suffix == '.csv'

    with out.open(newline='') as f:
        reader = csv.reader(f)
        rows = list(reader)

    assert len(rows) == 4  # header + 3 data rows
    header = [h.lower() for h in rows[0]]
    assert header == ['id', 'name', 'amount']
    assert rows[1][1] == 'Alice'
    assert rows[2][1] == 'Bob'
    assert rows[3][1] == 'Carol'


def test_report_e2e_excel(app, excel_report_id, tmp_path):
    openpyxl = pytest.importorskip('openpyxl')

    result = _run_report_step(app, excel_report_id, tmp_path)

    assert result.success, f"Step failed: {result.error}"
    assert result.rows_affected == 3

    out = tmp_path / 'e2e_test.xlsx'
    assert out.exists()
    assert out.suffix == '.xlsx'

    wb = openpyxl.load_workbook(out)
    assert 'TestSheet' in wb.sheetnames
    ws = wb['TestSheet']
    assert ws.max_row == 4  # header + 3 data rows

    header = [str(ws.cell(1, c).value).lower() for c in range(1, 4)]
    assert header == ['id', 'name', 'amount']
    assert ws.cell(2, 2).value == 'Alice'
    assert ws.cell(3, 2).value == 'Bob'
    assert ws.cell(4, 2).value == 'Carol'


def test_report_e2e_zero_rows(app, client, headers, report_conn_id, tmp_path):
    """A query returning zero rows still writes a file (header only for CSV)."""
    resp = client.post('/api/report-configs', json={
        'name': f'E2E Zero {uuid.uuid4().hex[:6]}',
        'connection_id': report_conn_id,
        'query': 'SELECT 1 AS id WHERE 1 = 0',
        'format': 'csv',
        'output_filename': 'e2e_zero.csv',
    }, headers=headers)
    assert resp.status_code == 201
    rid = resp.get_json()['id']

    try:
        result = _run_report_step(app, rid, tmp_path)
    finally:
        client.delete(f'/api/report-configs/{rid}', headers=headers)

    assert result.success, f"Step failed: {result.error}"
    assert result.rows_affected == 0

    out = tmp_path / 'e2e_zero.csv'
    assert out.exists()

    with out.open(newline='') as f:
        rows = list(csv.reader(f))

    assert len(rows) == 1  # header row only
    assert rows[0][0].lower() == 'id'


def test_report_e2e_output_path_in_result(app, csv_report_id, tmp_path):
    """result.output_path must be a non-empty string pointing to an existing file."""
    result = _run_report_step(app, csv_report_id, tmp_path)

    assert result.success, f"Step failed: {result.error}"
    assert result.output_path, "output_path should be set on success"
    from pathlib import Path
    assert Path(result.output_path).exists()
