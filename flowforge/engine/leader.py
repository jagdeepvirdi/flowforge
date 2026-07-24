"""Distributed leader election for the scheduler daemon, via Redis.

Problem: `flowforge/engine/scheduler.py` runs a `BlockingScheduler` that fires
cron jobs directly from its own process. Scaling the `scheduler` service past
one replica (or running multiple app instances that each also start a
scheduler) means every replica independently fires the same job — duplicate
pipeline runs, with no guard beyond the separate concurrency ceiling in
concurrency.py (which limits how many runs happen at once, not how many times
each cron tick fires).

Without FLOWFORGE_REDIS_URL: HA is not possible without a shared coordination
point, so election is skipped entirely (same convention as concurrency.py's
fallback) — the caller must not run more than one scheduler replica.

With FLOWFORGE_REDIS_URL: only one replica actually runs the scheduler at a
time. That replica holds a Redis key (`SET ... NX PX`) and renews it on a
timer in a background thread. If renewal ever fails — Redis unreachable, or
the key no longer holds this process's token (its TTL lapsed and another
replica took over) — this process is no longer safe to keep firing jobs, so
it exits immediately via os._exit(1) rather than risk two schedulers running
at once ("split brain"). The process manager (Docker/systemd/k8s) is expected
to restart it, at which point it re-enters the election as a fresh candidate.
"""
import logging
import os
import threading
import time
import uuid

logger = logging.getLogger(__name__)

_LOCK_KEY = 'flowforge:scheduler:leader'
_LOCK_TTL_SECONDS = 30
_RENEW_INTERVAL_SECONDS = 10
_ACQUIRE_POLL_SECONDS = 5

# Renew only if this process's token still owns the key — a plain SET would
# happily overwrite a lock some other replica has since acquired.
_RENEW_SCRIPT = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('PEXPIRE', KEYS[1], ARGV[2])
else
    return 0
end
"""

_RELEASE_SCRIPT = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
else
    return 0
end
"""


def ha_enabled() -> bool:
    return bool(os.environ.get('FLOWFORGE_REDIS_URL', ''))


def _redis_client():
    import redis
    # socket_timeout bounds command round-trips, not just the initial connect —
    # matches concurrency.py's client so a frozen/blackholed Redis can't hang
    # the acquire/renew loop indefinitely.
    return redis.from_url(
        os.environ['FLOWFORGE_REDIS_URL'], socket_connect_timeout=3, socket_timeout=3,
    )


def run_with_leadership(on_acquired) -> None:
    """Block until this process wins the scheduler leader lock, then call
    on_acquired() (expected to itself block, e.g. BlockingScheduler.start(),
    and to absorb its own KeyboardInterrupt/SystemExit so a graceful stop
    returns here to release the lock rather than propagating out).

    Retries indefinitely (polling every _ACQUIRE_POLL_SECONDS) while another
    replica holds the lock.
    """
    token = uuid.uuid4().hex
    client = _redis_client()

    while not client.set(_LOCK_KEY, token, nx=True, px=_LOCK_TTL_SECONDS * 1000):
        logger.info("HA: another instance holds the scheduler leader lock — waiting to become leader...")
        time.sleep(_ACQUIRE_POLL_SECONDS)

    logger.info("HA: acquired scheduler leader lock — this instance will fire scheduled jobs.")
    stop_renew = threading.Event()
    renew_thread = threading.Thread(
        target=_renew_loop, args=(client, token, stop_renew), daemon=True, name='ff-leader-renew',
    )
    renew_thread.start()

    try:
        on_acquired()
    finally:
        stop_renew.set()
        try:
            client.eval(_RELEASE_SCRIPT, 1, _LOCK_KEY, token)
        except Exception:
            logger.warning(
                "HA: failed to release scheduler leader lock on shutdown — it will expire "
                "via TTL (%ds) instead.", _LOCK_TTL_SECONDS,
            )


def _do_renew(client, token: str) -> bool:
    """Attempt one renewal. Returns True if this token still holds the lock."""
    try:
        return bool(client.eval(_RENEW_SCRIPT, 1, _LOCK_KEY, token, _LOCK_TTL_SECONDS * 1000))
    except Exception:
        logger.exception("HA: Redis error while renewing scheduler leader lock.")
        return False


def _renew_loop(client, token: str, stop_event: threading.Event) -> None:
    while not stop_event.wait(_RENEW_INTERVAL_SECONDS):
        if not _do_renew(client, token):
            logger.critical(
                "HA: lost the scheduler leader lock (token=%s) — exiting immediately so this "
                "process can't keep firing jobs alongside whichever replica now holds the lock "
                "(split-brain). The process manager should restart this instance.",
                token[:8],
            )
            os._exit(1)
            return
