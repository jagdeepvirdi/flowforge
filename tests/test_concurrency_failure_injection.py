"""Real failure-injection tests for flowforge/engine/concurrency.py.

Unlike test_concurrency.py (which mocks the `redis` module entirely), these
tests exercise the real redis-py client against real sockets: a genuine
connection-refused port, a real TCP server that accepts connections but never
responds (reproducing a frozen/blackholed Redis), and — when a real Redis is
reachable — real concurrent load against real Redis to prove the Lua-script
acquire path is actually atomic under concurrency, not just correct when
called sequentially in a mock.

This is what caught a real bug: _redis_client() previously set only
socket_connect_timeout, not socket_timeout, so a Redis that accepted the TCP
connection but then hung mid-command (e.g. frozen, overloaded) caused
try_acquire() to block indefinitely — silently defeating the documented
fail-open guarantee. Verified via `docker pause` against a real Redis
container during development; the hanging-server test below reproduces the
same failure mode without a Docker dependency so it runs anywhere.
"""
import contextlib
import os
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    from flowforge.engine.concurrency import _reset_for_tests
    _reset_for_tests()
    yield
    _reset_for_tests()


# ── real hanging TCP server (reproduces "Redis connected but frozen") ─────────

@contextlib.contextmanager
def _hanging_server():
    """A real TCP server that accepts connections but never writes a single
    byte back — indistinguishable, from the client's perspective, from a
    Redis process that is frozen (e.g. `docker pause`) or blackholed mid-command."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('127.0.0.1', 0))
    port = srv.getsockname()[1]
    srv.listen(5)
    stop = threading.Event()
    accepted: list[socket.socket] = []

    def _accept_loop():
        srv.settimeout(0.2)
        while not stop.is_set():
            try:
                conn, _ = srv.accept()
                accepted.append(conn)  # accept but never read or write
            except TimeoutError:
                continue
            except OSError:
                break

    t = threading.Thread(target=_accept_loop, daemon=True)
    t.start()
    try:
        yield port
    finally:
        stop.set()
        t.join(timeout=2)
        for c in accepted:
            with contextlib.suppress(Exception):
                c.close()
        with contextlib.suppress(Exception):
            srv.close()


def test_try_acquire_bounded_when_redis_hangs(monkeypatch):
    """Regression test for the missing socket_timeout bug.

    A Redis that accepts the connection but never responds must still cause
    try_acquire() to fail open within a bounded time — not hang forever.
    """
    with _hanging_server() as port:
        monkeypatch.setenv('FLOWFORGE_REDIS_URL', f'redis://127.0.0.1:{port}/0')
        from flowforge.engine.concurrency import try_acquire

        start = time.monotonic()
        token = try_acquire()
        elapsed = time.monotonic() - start

    assert token is not None, 'a hung Redis must still fail open (non-None token)'
    assert elapsed < 10, (
        f'try_acquire() took {elapsed:.1f}s against a hanging Redis — '
        'socket_timeout regression (should fail open in a few seconds)'
    )


def test_release_bounded_when_redis_hangs(monkeypatch):
    """release() must also not hang forever against a frozen Redis."""
    with _hanging_server() as port:
        monkeypatch.setenv('FLOWFORGE_REDIS_URL', f'redis://127.0.0.1:{port}/0')
        from flowforge.engine.concurrency import release

        start = time.monotonic()
        release('some-real-looking-token')  # must not raise or hang
        elapsed = time.monotonic() - start

    assert elapsed < 10, f'release() took {elapsed:.1f}s against a hanging Redis'


def test_try_acquire_bounded_when_connection_refused(monkeypatch):
    """A cleanly-refused connection (nothing listening) must also fail open quickly."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('127.0.0.1', 0))
    free_port = sock.getsockname()[1]
    sock.close()  # port is now guaranteed unbound — connection will be refused

    monkeypatch.setenv('FLOWFORGE_REDIS_URL', f'redis://127.0.0.1:{free_port}/0')
    from flowforge.engine.concurrency import try_acquire

    start = time.monotonic()
    token = try_acquire()
    elapsed = time.monotonic() - start

    assert token is not None
    assert elapsed < 10, f'try_acquire() took {elapsed:.1f}s against a refused connection'


# ── real concurrent load against a real Redis (when available) ────────────────

def _real_redis_url() -> str | None:
    url = os.environ.get('FLOWFORGE_TEST_REDIS_URL', 'redis://localhost:6379/15')
    try:
        import redis
        redis.from_url(url, socket_connect_timeout=1, socket_timeout=1).ping()
        return url
    except Exception:
        return None


_REAL_REDIS_URL = _real_redis_url()


@pytest.mark.skipif(_REAL_REDIS_URL is None, reason='no real Redis reachable for load testing')
def test_real_redis_enforces_exact_limit_under_concurrent_load(monkeypatch):
    """Hammer try_acquire() from many real threads against a real Redis and
    verify the Lua script enforces FLOWFORGE_MAX_CONCURRENT_RUNS exactly —
    no more, no fewer — proving atomicity under genuine concurrency (not a
    sequential mock)."""
    monkeypatch.setenv('FLOWFORGE_REDIS_URL', _REAL_REDIS_URL)
    monkeypatch.setenv('FLOWFORGE_MAX_CONCURRENT_RUNS', '10')
    from flowforge.engine.concurrency import try_acquire

    results = []
    lock = threading.Lock()

    def _attempt():
        token = try_acquire()
        with lock:
            results.append(token)

    with ThreadPoolExecutor(max_workers=50) as pool:
        list(pool.map(lambda _: _attempt(), range(50)))

    granted = [t for t in results if t is not None]
    assert len(granted) == 10, (
        f'expected exactly 10 slots granted out of 50 concurrent attempts, got {len(granted)} — '
        'possible race condition in the Redis Lua acquire script'
    )
    assert len(set(granted)) == 10, 'duplicate tokens granted — token uniqueness violated'


@pytest.mark.skipif(_REAL_REDIS_URL is None, reason='no real Redis reachable for load testing')
def test_real_redis_release_frees_slot_for_next_acquirer(monkeypatch):
    monkeypatch.setenv('FLOWFORGE_REDIS_URL', _REAL_REDIS_URL)
    monkeypatch.setenv('FLOWFORGE_MAX_CONCURRENT_RUNS', '1')
    from flowforge.engine.concurrency import release, try_acquire

    t1 = try_acquire()
    assert t1 is not None
    assert try_acquire() is None  # limit reached
    release(t1)
    t2 = try_acquire()
    assert t2 is not None
    release(t2)
