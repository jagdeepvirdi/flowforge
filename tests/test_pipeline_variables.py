"""
Pipeline variable tests:
- Secret vars are encrypted at rest (DB value ≠ plaintext)
- Secret vars are decrypted correctly by load_pipeline()
- {{ vars.key }} and {{ key }} both resolve in the Jinja2 context
- Plaintext non-secret vars are stored as-is and unaffected by crypto
"""
import pytest

from flowforge.crypto import decrypt_value


@pytest.fixture()
def pipeline_with_vars(client, headers):
    """Create a pipeline with one secret and one plaintext variable, clean up after."""
    resp = client.post('/api/pipelines', json={
        'name': '__test_vars_pipeline__',
        'variables': [
            {'var_key': 'secret_token', 'var_value': 'hunter2', 'is_secret': True},
            {'var_key': 'report_month', 'var_value': '2026-05', 'is_secret': False},
        ],
    }, headers=headers)
    assert resp.status_code == 201, resp.get_json()
    data = resp.get_json()
    yield data
    client.delete(f'/api/pipelines/{data["id"]}', headers=headers)


def test_secret_var_masked_in_api_response(pipeline_with_vars):
    """API must never return the plaintext value of a secret var."""
    secret_var = next(v for v in pipeline_with_vars['variables'] if v['var_key'] == 'secret_token')
    assert secret_var['var_value'] == '***'
    assert secret_var['is_secret'] is True


def test_secret_var_encrypted_in_db(app, pipeline_with_vars):
    """The raw DB value of a secret var must not be the plaintext."""
    from flowforge.db.models import PipelineVariable, db

    with app.app_context():
        var = db.session.query(PipelineVariable).filter_by(
            pipeline_id=pipeline_with_vars['id'],
            var_key='secret_token',
        ).one()
        assert var.var_value != 'hunter2', 'Secret var stored as plaintext — encryption not applied'
        # Must be AES-GCM ciphertext: decoding it should give back the original
        assert decrypt_value(var.var_value) == 'hunter2'


def test_plaintext_var_not_encrypted_in_db(app, pipeline_with_vars):
    """Non-secret vars must be stored verbatim, not encrypted."""
    from flowforge.db.models import PipelineVariable, db

    with app.app_context():
        var = db.session.query(PipelineVariable).filter_by(
            pipeline_id=pipeline_with_vars['id'],
            var_key='report_month',
        ).one()
        assert var.var_value == '2026-05'
        assert var.is_secret is False


def test_secret_var_decrypted_at_runtime(app, pipeline_with_vars):
    """load_pipeline() must return the decrypted plaintext for secret vars."""
    from flowforge.engine.loader import load_pipeline

    with app.app_context():
        _steps, pipeline_vars, _sk = load_pipeline(pipeline_with_vars['id'])
        assert pipeline_vars.get('secret_token') == 'hunter2'
        assert pipeline_vars.get('report_month') == '2026-05'


def test_vars_available_in_context(app, pipeline_with_vars):
    """Both {{ key }} and {{ vars.key }} must resolve in the Jinja2 pipeline context."""
    from flowforge.engine import context
    from flowforge.engine.loader import load_pipeline

    with app.app_context():
        _steps, pipeline_vars, _sk = load_pipeline(pipeline_with_vars['id'])

    ctx = context.build(
        pipeline_name='__test_vars_pipeline__',
        pipeline_vars=pipeline_vars,
    )

    # Flat access
    assert context.render('{{ secret_token }}', ctx) == 'hunter2'
    assert context.render('{{ report_month }}', ctx) == '2026-05'

    # vars. namespace access
    assert context.render('{{ vars.secret_token }}', ctx) == 'hunter2'
    assert context.render('{{ vars.report_month }}', ctx) == '2026-05'


def test_secret_var_not_leaked_by_update(app, pipeline_with_vars, headers, client):
    """GET /pipelines/:id must still mask the secret on a subsequent fetch."""
    resp = client.get(f'/api/pipelines/{pipeline_with_vars["id"]}', headers=headers)
    assert resp.status_code == 200
    secret_var = next(v for v in resp.get_json()['variables'] if v['var_key'] == 'secret_token')
    assert secret_var['var_value'] == '***'


# ── PUT variable replacement ───────────────────────────────────────────────

def test_put_adds_new_variable(pipeline_with_vars, headers, client):
    """PUT with an extra var should append it; existing vars replaced in full."""
    pid = pipeline_with_vars['id']
    resp = client.put(f'/api/pipelines/{pid}', json={
        'variables': [
            {'var_key': 'secret_token', 'var_value': 'hunter2', 'is_secret': True},
            {'var_key': 'report_month', 'var_value': '2026-05', 'is_secret': False},
            {'var_key': 'region', 'var_value': 'APAC', 'is_secret': False},
        ],
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    keys = [v['var_key'] for v in data['variables']]
    assert 'region' in keys
    assert len(data['variables']) == 3


def test_put_removes_variable(pipeline_with_vars, headers, client):
    """PUT with a shorter list should delete vars not included."""
    pid = pipeline_with_vars['id']
    resp = client.put(f'/api/pipelines/{pid}', json={
        'variables': [
            {'var_key': 'report_month', 'var_value': '2026-06', 'is_secret': False},
        ],
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    keys = [v['var_key'] for v in data['variables']]
    assert 'secret_token' not in keys
    assert keys == ['report_month']


def test_put_modifies_variable_value(pipeline_with_vars, headers, client, app):
    """PUT should update the stored value of an existing non-secret var."""
    pid = pipeline_with_vars['id']
    resp = client.put(f'/api/pipelines/{pid}', json={
        'variables': [
            {'var_key': 'report_month', 'var_value': '2026-06', 'is_secret': False},
        ],
    }, headers=headers)
    assert resp.status_code == 200
    from flowforge.db.models import PipelineVariable, db
    with app.app_context():
        var = db.session.query(PipelineVariable).filter_by(
            pipeline_id=pid, var_key='report_month'
        ).one()
        assert var.var_value == '2026-06'


def test_put_empty_variables_clears_all(pipeline_with_vars, headers, client):
    """PUT with variables=[] should remove all vars."""
    pid = pipeline_with_vars['id']
    resp = client.put(f'/api/pipelines/{pid}', json={'variables': []}, headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['variables'] == []


# ── last_success_at runner injection ──────────────────────────────────────

def test_last_success_at_empty_on_first_run(app, pipeline_with_vars):
    """When no successful run exists last_success_at must be an empty string."""
    from flowforge.engine.runner import _get_last_success_ts

    with app.app_context():
        val = _get_last_success_ts(pipeline_with_vars['id'], '%Y%m%d%H%M%S')
    assert val == ''


def test_last_success_at_set_after_successful_run(app, pipeline_with_vars):
    """_get_last_success_ts returns the finished_at of the most recent success."""
    from datetime import datetime
    from flowforge.db.models import PipelineRun, db
    from flowforge.engine.runner import _get_last_success_ts

    pid = pipeline_with_vars['id']
    # Use a naive datetime so there is no timezone conversion on INSERT/SELECT.
    ts = datetime(2026, 4, 15, 12, 30, 0)

    with app.app_context():
        run = PipelineRun(
            pipeline_id=pid,
            pipeline_name='__test_vars_pipeline__',
            status='success',
            triggered_by='test',
            finished_at=ts,
        )
        db.session.add(run)
        db.session.commit()
        run_id = run.id

        val_ts = _get_last_success_ts(pid, '%Y%m%d%H%M%S')
        val_date = _get_last_success_ts(pid, '%Y-%m-%d')

        db.session.delete(db.session.get(PipelineRun, run_id))
        db.session.commit()

    assert val_ts == '20260415123000'
    assert val_date == '2026-04-15'


def test_last_success_at_picks_most_recent(app, pipeline_with_vars):
    """When multiple successful runs exist the most recent finished_at is returned."""
    from datetime import datetime
    from flowforge.db.models import PipelineRun, db
    from flowforge.engine.runner import _get_last_success_ts

    pid = pipeline_with_vars['id']
    run_ids = []

    with app.app_context():
        for day in (10, 15, 5):
            run = PipelineRun(
                pipeline_id=pid,
                pipeline_name='__test__',
                status='success',
                triggered_by='test',
                finished_at=datetime(2026, 4, day, 0, 0, 0),  # naive — no tz conversion
            )
            db.session.add(run)
        db.session.commit()
        for run in db.session.query(PipelineRun).filter_by(pipeline_id=pid).all():
            run_ids.append(run.id)

        result = _get_last_success_ts(pid, '%Y-%m-%d')

        for rid in run_ids:
            db.session.delete(db.session.get(PipelineRun, rid))
        db.session.commit()

    assert result == '2026-04-15'
