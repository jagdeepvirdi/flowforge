"""Unit tests for flowforge/engine/concurrency.py."""
import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    """Depends on monkeypatch so our post-test reset runs before it reverts
    FLOWFORGE_REDIS_URL — otherwise a real reachable Redis (as in this dev
    environment) would leak slots across tests."""
    from flowforge.engine.concurrency import _reset_for_tests
    _reset_for_tests()
    yield
    _reset_for_tests()


# ── local (no Redis) fallback ──────────────────────────────────────────────────

def test_local_acquire_returns_token(monkeypatch):
    monkeypatch.delenv('FLOWFORGE_REDIS_URL', raising=False)
    from flowforge.engine.concurrency import try_acquire
    token = try_acquire()
    assert token is not None


def test_local_acquire_up_to_limit_then_denied(monkeypatch):
    monkeypatch.delenv('FLOWFORGE_REDIS_URL', raising=False)
    monkeypatch.setenv('FLOWFORGE_MAX_CONCURRENT_RUNS', '2')
    from flowforge.engine.concurrency import try_acquire
    t1 = try_acquire()
    t2 = try_acquire()
    t3 = try_acquire()
    assert t1 is not None
    assert t2 is not None
    assert t3 is None


def test_local_release_frees_a_slot(monkeypatch):
    monkeypatch.delenv('FLOWFORGE_REDIS_URL', raising=False)
    monkeypatch.setenv('FLOWFORGE_MAX_CONCURRENT_RUNS', '1')
    from flowforge.engine.concurrency import release, try_acquire
    t1 = try_acquire()
    assert t1 is not None
    assert try_acquire() is None  # limit reached
    release(t1)
    assert try_acquire() is not None  # slot freed


def test_release_none_is_noop(monkeypatch):
    monkeypatch.delenv('FLOWFORGE_REDIS_URL', raising=False)
    from flowforge.engine.concurrency import release
    release(None)  # must not raise


def test_default_max_concurrent_is_five(monkeypatch):
    monkeypatch.delenv('FLOWFORGE_MAX_CONCURRENT_RUNS', raising=False)
    from flowforge.engine.concurrency import _max_concurrent
    assert _max_concurrent() == 5


# ── Redis-backed distributed counter ───────────────────────────────────────────

def _mock_redis_module(eval_return):
    client = MagicMock()
    client.eval.return_value = eval_return
    redis_mod = ModuleType('redis')
    redis_mod.from_url = MagicMock(return_value=client)
    return redis_mod, client


def test_redis_acquire_success_returns_token(monkeypatch):
    monkeypatch.setenv('FLOWFORGE_REDIS_URL', 'redis://localhost:6379/0')
    redis_mod, client = _mock_redis_module(1)
    monkeypatch.setitem(sys.modules, 'redis', redis_mod)
    from flowforge.engine.concurrency import try_acquire
    token = try_acquire()
    assert token is not None
    client.eval.assert_called_once()


def test_redis_acquire_denied_returns_none(monkeypatch):
    monkeypatch.setenv('FLOWFORGE_REDIS_URL', 'redis://localhost:6379/0')
    redis_mod, client = _mock_redis_module(0)
    monkeypatch.setitem(sys.modules, 'redis', redis_mod)
    from flowforge.engine.concurrency import try_acquire
    assert try_acquire() is None


def test_redis_unreachable_fails_open(monkeypatch):
    """A Redis outage must not block pipeline execution — fail open with a marker token."""
    monkeypatch.setenv('FLOWFORGE_REDIS_URL', 'redis://localhost:6379/0')
    client = MagicMock()
    client.eval.side_effect = ConnectionError('boom')
    redis_mod = ModuleType('redis')
    redis_mod.from_url = MagicMock(return_value=client)
    monkeypatch.setitem(sys.modules, 'redis', redis_mod)
    from flowforge.engine.concurrency import try_acquire
    token = try_acquire()
    assert token is not None


def test_redis_release_calls_zrem(monkeypatch):
    monkeypatch.setenv('FLOWFORGE_REDIS_URL', 'redis://localhost:6379/0')
    redis_mod, client = _mock_redis_module(1)
    monkeypatch.setitem(sys.modules, 'redis', redis_mod)
    from flowforge.engine.concurrency import release, try_acquire
    token = try_acquire()
    release(token)
    client.zrem.assert_called_once()


def test_redis_release_swallows_errors(monkeypatch):
    monkeypatch.setenv('FLOWFORGE_REDIS_URL', 'redis://localhost:6379/0')
    redis_mod, client = _mock_redis_module(1)
    client.zrem.side_effect = ConnectionError('boom')
    monkeypatch.setitem(sys.modules, 'redis', redis_mod)
    from flowforge.engine.concurrency import release, try_acquire
    token = try_acquire()
    release(token)  # must not raise


def test_redis_down_marker_token_release_is_noop(monkeypatch):
    """release() must not try to zrem the fail-open marker token."""
    monkeypatch.setenv('FLOWFORGE_REDIS_URL', 'redis://localhost:6379/0')
    client = MagicMock()
    client.eval.side_effect = ConnectionError('boom')
    redis_mod = ModuleType('redis')
    redis_mod.from_url = MagicMock(return_value=client)
    monkeypatch.setitem(sys.modules, 'redis', redis_mod)
    from flowforge.engine.concurrency import release, try_acquire
    token = try_acquire()
    client.reset_mock()
    release(token)
    client.zrem.assert_not_called()


def test_uses_redis_when_url_set_not_local(monkeypatch):
    """When FLOWFORGE_REDIS_URL is set, the local semaphore must not be touched."""
    monkeypatch.setenv('FLOWFORGE_REDIS_URL', 'redis://localhost:6379/0')
    monkeypatch.setenv('FLOWFORGE_MAX_CONCURRENT_RUNS', '1')
    redis_mod, client = _mock_redis_module(1)
    monkeypatch.setitem(sys.modules, 'redis', redis_mod)
    from flowforge.engine.concurrency import try_acquire
    # Would be denied by a size-1 local semaphore on the 2nd call, but Redis
    # mock always returns "acquired" — proves the local path isn't used.
    assert try_acquire() is not None
    assert try_acquire() is not None
