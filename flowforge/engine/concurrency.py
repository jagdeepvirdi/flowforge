"""Enforces FLOWFORGE_MAX_CONCURRENT_RUNS across the whole deployment.

- FLOWFORGE_REDIS_URL unset: falls back to an in-process threading.Semaphore.
  Correct only within a single worker process (same limitation the old,
  since-regressed semaphore had) — fine for `flowforge web` / a single
  Gunicorn worker / local dev.
- FLOWFORGE_REDIS_URL set: uses a Redis sorted set as a distributed counter,
  so the limit holds across multiple Gunicorn workers and/or multiple Celery
  workers. Slots carry a TTL so a crashed process can't permanently hold one.

Single entry point: try_acquire() / release(token) around launch_run() in
flowforge/engine/launcher.py, covering every trigger path (HTTP, webhook,
scheduler, downstream dependency fan-out).
"""
import logging
import os
import threading
import time
import uuid

logger = logging.getLogger(__name__)

_REDIS_KEY = 'flowforge:concurrent_runs'
_SLOT_TTL_SECONDS = 3600  # safety valve if release() is never called (crash)

_LOCAL_UNAVAILABLE_TOKEN = 'local'  # nosec B105 — a slot-token marker, not a credential
_REDIS_DOWN_TOKEN = 'redis-unavailable'  # nosec B105 — fail-open marker, see _try_acquire_redis

_local_semaphore: threading.Semaphore | None = None
_local_semaphore_lock = threading.Lock()

_ACQUIRE_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local expires_at = tonumber(ARGV[2])
local token = ARGV[3]
local max_n = tonumber(ARGV[4])
redis.call('ZREMRANGEBYSCORE', key, '-inf', now)
local count = redis.call('ZCARD', key)
if count >= max_n then
    return 0
end
redis.call('ZADD', key, expires_at, token)
redis.call('EXPIRE', key, ARGV[5])
return 1
"""


def _max_concurrent() -> int:
    return int(os.environ.get('FLOWFORGE_MAX_CONCURRENT_RUNS', '5'))


def _redis_url() -> str:
    return os.environ.get('FLOWFORGE_REDIS_URL', '')


def try_acquire() -> str | None:
    """Reserve a concurrency slot. Returns an opaque token to pass to release(),
    or None if the deployment is already at FLOWFORGE_MAX_CONCURRENT_RUNS."""
    redis_url = _redis_url()
    if redis_url:
        return _try_acquire_redis(redis_url)
    return _try_acquire_local()


def release(token: str | None) -> None:
    """Release a slot previously returned by try_acquire(). No-op for None
    (i.e. try_acquire() denied the slot in the first place)."""
    if token is None:
        return
    if token == _REDIS_DOWN_TOKEN:
        return
    redis_url = _redis_url()
    if redis_url:
        _release_redis(redis_url, token)
    else:
        _release_local()


# ── in-process fallback (no Redis configured) ──────────────────────────────

def _get_local_semaphore() -> threading.Semaphore:
    global _local_semaphore
    with _local_semaphore_lock:
        if _local_semaphore is None:
            _local_semaphore = threading.Semaphore(_max_concurrent())
        return _local_semaphore


def _try_acquire_local() -> str | None:
    if _get_local_semaphore().acquire(blocking=False):
        return _LOCAL_UNAVAILABLE_TOKEN
    return None


def _reset_for_tests() -> None:
    """Test-only: drop the in-process semaphore so it's rebuilt (with the
    current FLOWFORGE_MAX_CONCURRENT_RUNS) on next use, and clear any slots
    left acquired (locally, or for real in Redis if one happens to be
    reachable in the test environment) by tests that mock away the
    release path."""
    global _local_semaphore
    with _local_semaphore_lock:
        _local_semaphore = None

    if _redis_url():
        try:
            _redis_client().delete(_REDIS_KEY)
        except Exception:  # nosec B110 — test-only best-effort cleanup
            pass


def _release_local() -> None:
    if _local_semaphore is not None:
        _local_semaphore.release()


# ── Redis-backed distributed counter ───────────────────────────────────────

def _redis_client():
    import redis
    # socket_timeout bounds command round-trips (not just the initial connect) —
    # without it, a Redis that accepts the TCP connection but never responds
    # (e.g. frozen, overloaded, or blackholed mid-command) hangs try_acquire()
    # indefinitely, defeating the fail-open guarantee below.
    return redis.from_url(_redis_url(), socket_connect_timeout=3, socket_timeout=3)


def _try_acquire_redis(redis_url: str) -> str | None:
    try:
        r = _redis_client()
        token = uuid.uuid4().hex
        now = time.time()
        acquired = r.eval(
            _ACQUIRE_SCRIPT,
            1,
            _REDIS_KEY,
            now,
            now + _SLOT_TTL_SECONDS,
            token,
            _max_concurrent(),
            _SLOT_TTL_SECONDS,
        )
        return token if acquired == 1 else None
    except Exception:
        # Fail-open: a Redis outage shouldn't block pipeline execution entirely.
        logger.exception("Redis concurrency check failed for %s — allowing run through", redis_url)
        return _REDIS_DOWN_TOKEN


def _release_redis(redis_url: str, token: str) -> None:
    try:
        _redis_client().zrem(_REDIS_KEY, token)
    except Exception:
        logger.exception("Failed to release Redis concurrency slot for %s", redis_url)
