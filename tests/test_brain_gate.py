"""Tests for the Brain attach gate (flowforge/brain.py)."""
from flowforge.brain import brain_enabled, brain_unavailable_response


def test_brain_disabled_in_phase_a(monkeypatch):
    monkeypatch.setenv('FLOWFORGE_BRAIN_URL', 'http://brain.example:8000')
    assert brain_enabled() is False


def test_brain_unavailable_response_shape(app):
    with app.test_request_context():
        resp, status = brain_unavailable_response()
    assert status == 503
    body = resp.get_json()
    assert body['error'] == 'brain_not_attached'
    assert 'FLOWFORGE_BRAIN_URL' in body['message']
