"""Tests for engine/shutdown.py — graceful shutdown coordination."""
import threading
import time
from unittest.mock import MagicMock, patch, call

import pytest


@pytest.fixture(autouse=True)
def reset_shutdown_state():
    """Reset the module-level state before every test."""
    import flowforge.engine.shutdown as sd
    sd._shutdown_event.clear()
    sd._active_runs.clear()
    sd._app = None
    yield
    sd._shutdown_event.clear()
    sd._active_runs.clear()
    sd._app = None


# ── register / unregister ─────────────────────────────────────────────────────

def test_register_adds_run():
    import flowforge.engine.shutdown as sd
    sd.register_run('run-1')
    assert 'run-1' in sd._active_runs


def test_unregister_removes_run():
    import flowforge.engine.shutdown as sd
    sd.register_run('run-1')
    sd.unregister_run('run-1')
    assert 'run-1' not in sd._active_runs


def test_unregister_missing_run_is_noop():
    import flowforge.engine.shutdown as sd
    sd.unregister_run('not-registered')  # must not raise


def test_multiple_runs_tracked():
    import flowforge.engine.shutdown as sd
    sd.register_run('a')
    sd.register_run('b')
    assert sd._active_runs == {'a', 'b'}
    sd.unregister_run('a')
    assert sd._active_runs == {'b'}


# ── is_shutdown_requested ────────────────────────────────────────────────────

def test_shutdown_not_requested_initially():
    from flowforge.engine.shutdown import is_shutdown_requested
    assert is_shutdown_requested() is False


def test_shutdown_requested_after_event_set():
    import flowforge.engine.shutdown as sd
    sd._shutdown_event.set()
    assert sd.is_shutdown_requested() is True


# ── _drain ───────────────────────────────────────────────────────────────────

def test_drain_returns_true_when_no_active_runs():
    from flowforge.engine.shutdown import _drain
    result = _drain(timeout=5)
    assert result is True


def test_drain_returns_true_when_run_finishes_in_time():
    import flowforge.engine.shutdown as sd
    sd.register_run('fast-run')

    def finish_soon():
        time.sleep(0.1)
        sd.unregister_run('fast-run')

    t = threading.Thread(target=finish_soon)
    t.start()
    result = sd._drain(timeout=5)
    t.join()
    assert result is True


def test_drain_returns_false_on_timeout():
    import flowforge.engine.shutdown as sd
    sd.register_run('stuck-run')
    result = sd._drain(timeout=1)
    assert result is False


# ── graceful_exit ────────────────────────────────────────────────────────────

def test_graceful_exit_sets_shutdown_event():
    import flowforge.engine.shutdown as sd
    mock_app = MagicMock()
    mock_app.app_context.return_value.__enter__ = MagicMock(return_value=None)
    mock_app.app_context.return_value.__exit__ = MagicMock(return_value=False)

    sd.graceful_exit(mock_app, timeout=1)
    assert sd.is_shutdown_requested() is True


def test_graceful_exit_clean_when_no_runs():
    import flowforge.engine.shutdown as sd
    mock_app = MagicMock()
    mock_app.app_context.return_value.__enter__ = MagicMock(return_value=None)
    mock_app.app_context.return_value.__exit__ = MagicMock(return_value=False)

    sd.graceful_exit(mock_app, timeout=2)
    # No stuck runs → should not have called cancel
    assert sd._app is mock_app


# ── _cancel_stuck_runs ───────────────────────────────────────────────────────

def test_cancel_stuck_runs_noop_when_app_is_none():
    import flowforge.engine.shutdown as sd
    sd._app = None
    sd._cancel_stuck_runs()  # must not raise


def test_cancel_stuck_runs_marks_running_as_cancelled():
    import flowforge.engine.shutdown as sd

    mock_app = MagicMock()
    ctx = MagicMock()
    mock_app.app_context.return_value = ctx
    ctx.__enter__ = MagicMock(return_value=None)
    ctx.__exit__ = MagicMock(return_value=False)

    sd._active_runs.add('stuck')
    sd._app = mock_app

    with patch.object(sd, '_drain', return_value=False), \
         patch.object(sd, '_cancel_stuck_runs') as mock_cancel:
        sd.graceful_exit(mock_app, timeout=0)
        mock_cancel.assert_called_once()


def test_cancel_stuck_runs_no_stuck_runs(app):
    """Integration: _cancel_stuck_runs with no running rows is a noop."""
    import flowforge.engine.shutdown as sd
    sd._app = app
    sd._cancel_stuck_runs()  # must not raise or error


# ── install_handler ──────────────────────────────────────────────────────────

def test_install_handler_sets_app():
    import flowforge.engine.shutdown as sd
    mock_app = MagicMock()
    with patch('signal.signal'), patch('atexit.register'):
        sd.install_handler(mock_app)
    assert sd._app is mock_app


def test_sigterm_handler_drains_and_exits():
    """The SIGTERM handler must call _drain and then raise SystemExit(0)."""
    import flowforge.engine.shutdown as sd
    mock_app = MagicMock()

    captured_handler = {}

    def capture_signal(sig, handler):
        captured_handler['handler'] = handler

    with patch('signal.signal', side_effect=capture_signal), \
         patch('atexit.register'):
        sd.install_handler(mock_app)

    handler = captured_handler.get('handler')
    assert handler is not None

    with patch.object(sd, '_drain', return_value=True), \
         pytest.raises(SystemExit) as exc_info:
        handler(15, None)

    assert exc_info.value.code == 0


def test_sigterm_handler_cancels_stuck_runs_on_timeout():
    """When _drain times out, _cancel_stuck_runs is called before SystemExit."""
    import flowforge.engine.shutdown as sd
    mock_app = MagicMock()

    captured_handler = {}

    def capture_signal(sig, handler):
        captured_handler['handler'] = handler

    with patch('signal.signal', side_effect=capture_signal), \
         patch('atexit.register'):
        sd.install_handler(mock_app)

    with patch.object(sd, '_drain', return_value=False), \
         patch.object(sd, '_cancel_stuck_runs') as mock_cancel, \
         pytest.raises(SystemExit):
        captured_handler['handler'](15, None)

    mock_cancel.assert_called_once()
