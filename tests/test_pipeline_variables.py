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
