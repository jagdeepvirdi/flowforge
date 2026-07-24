"""Unit tests for flowforge/engine/leader.py — Redis-backed scheduler leader election."""
import threading
from unittest.mock import MagicMock, patch

import flowforge.engine.leader as leader_mod


# ── ha_enabled ──────────────────────────────────────────────────────────────

def test_ha_enabled_true_when_redis_url_set(monkeypatch):
    monkeypatch.setenv('FLOWFORGE_REDIS_URL', 'redis://localhost:6379/0')
    assert leader_mod.ha_enabled() is True


def test_ha_enabled_false_when_redis_url_unset(monkeypatch):
    monkeypatch.delenv('FLOWFORGE_REDIS_URL', raising=False)
    assert leader_mod.ha_enabled() is False


# ── run_with_leadership ───────────────────────────────────────────────────

def test_run_with_leadership_acquires_immediately_and_calls_on_acquired():
    mock_client = MagicMock()
    mock_client.set.return_value = True

    on_acquired = MagicMock()

    with patch.object(leader_mod, '_redis_client', return_value=mock_client), \
         patch.object(leader_mod.threading, 'Thread') as mock_thread_cls:
        mock_thread = MagicMock()
        mock_thread_cls.return_value = mock_thread

        leader_mod.run_with_leadership(on_acquired)

    on_acquired.assert_called_once()
    mock_thread.start.assert_called_once()
    # Lock released on the way out
    mock_client.eval.assert_called_once()
    assert mock_client.eval.call_args[0][0] == leader_mod._RELEASE_SCRIPT


def test_run_with_leadership_retries_until_acquired():
    mock_client = MagicMock()
    mock_client.set.side_effect = [False, False, True]

    on_acquired = MagicMock()

    with patch.object(leader_mod, '_redis_client', return_value=mock_client), \
         patch.object(leader_mod.time, 'sleep') as mock_sleep, \
         patch.object(leader_mod.threading, 'Thread') as mock_thread_cls:
        mock_thread_cls.return_value = MagicMock()
        leader_mod.run_with_leadership(on_acquired)

    assert mock_client.set.call_count == 3
    assert mock_sleep.call_count == 2
    on_acquired.assert_called_once()


def test_run_with_leadership_releases_lock_even_if_on_acquired_raises():
    mock_client = MagicMock()
    mock_client.set.return_value = True

    def _boom():
        raise RuntimeError('scheduler crashed')

    with patch.object(leader_mod, '_redis_client', return_value=mock_client), \
         patch.object(leader_mod.threading, 'Thread') as mock_thread_cls:
        mock_thread_cls.return_value = MagicMock()
        try:
            leader_mod.run_with_leadership(_boom)
            raised = False
        except RuntimeError:
            raised = True

    assert raised
    mock_client.eval.assert_called_once()
    assert mock_client.eval.call_args[0][0] == leader_mod._RELEASE_SCRIPT


def test_run_with_leadership_release_failure_does_not_raise():
    """A Redis error during the release-on-exit path must not mask the real outcome."""
    mock_client = MagicMock()
    mock_client.set.return_value = True
    mock_client.eval.side_effect = Exception('redis down')

    on_acquired = MagicMock()

    with patch.object(leader_mod, '_redis_client', return_value=mock_client), \
         patch.object(leader_mod.threading, 'Thread') as mock_thread_cls:
        mock_thread_cls.return_value = MagicMock()
        leader_mod.run_with_leadership(on_acquired)  # must not raise

    on_acquired.assert_called_once()


# ── _do_renew ───────────────────────────────────────────────────────────────

def test_do_renew_true_when_token_still_owns_lock():
    mock_client = MagicMock()
    mock_client.eval.return_value = 1
    assert leader_mod._do_renew(mock_client, 'tok') is True


def test_do_renew_false_when_lock_lost():
    mock_client = MagicMock()
    mock_client.eval.return_value = 0
    assert leader_mod._do_renew(mock_client, 'tok') is False


def test_do_renew_false_on_redis_error():
    mock_client = MagicMock()
    mock_client.eval.side_effect = Exception('connection reset')
    assert leader_mod._do_renew(mock_client, 'tok') is False


# ── _renew_loop ───────────────────────────────────────────────────────────

def test_renew_loop_exits_cleanly_when_stop_event_already_set():
    mock_client = MagicMock()
    stop_event = threading.Event()
    stop_event.set()

    with patch.object(leader_mod, '_do_renew') as mock_do_renew, \
         patch.object(leader_mod.os, '_exit') as mock_exit:
        leader_mod._renew_loop(mock_client, 'tok', stop_event)

    mock_do_renew.assert_not_called()
    mock_exit.assert_not_called()


def test_renew_loop_exits_process_when_renewal_fails():
    mock_client = MagicMock()
    stop_event = MagicMock()
    # First wait() returns False (renew), second returns True (would-be exit,
    # but os._exit is mocked so the loop's `return` after it ends the call).
    stop_event.wait.side_effect = [False, True]

    with patch.object(leader_mod, '_do_renew', return_value=False), \
         patch.object(leader_mod.os, '_exit') as mock_exit:
        leader_mod._renew_loop(mock_client, 'tok', stop_event)

    mock_exit.assert_called_once_with(1)


def test_renew_loop_keeps_going_while_renewal_succeeds():
    mock_client = MagicMock()
    stop_event = MagicMock()
    stop_event.wait.side_effect = [False, False, True]

    with patch.object(leader_mod, '_do_renew', return_value=True) as mock_do_renew, \
         patch.object(leader_mod.os, '_exit') as mock_exit:
        leader_mod._renew_loop(mock_client, 'tok', stop_event)

    assert mock_do_renew.call_count == 2
    mock_exit.assert_not_called()
