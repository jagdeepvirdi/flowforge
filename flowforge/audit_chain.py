"""Tamper-evident audit log: a keyed hash chain over ``ff_audit_log`` plus a maintenance gate.

What this gives you, and what it does not (keep these honest in docs and sales material):

* **Prevention against accidents and app-level attacks.** A database trigger refuses UPDATE,
  DELETE and TRUNCATE on ``ff_audit_log`` unless the transaction has set
  ``flowforge.audit_maintenance = 'on'``. Only the retention prune and the GDPR purge in this
  module set it. An attacker who can run arbitrary SQL *as the table owner* can set the flag or
  drop the trigger, so this is not a defence against a compromised database owner.
* **Detection against that attacker.** Every chained row stores ``prev_hash`` and
  ``row_hash = HMAC-SHA256(key, seq | prev_hash | content_digest)``. Editing a row, deleting one in
  the middle, or reordering rows breaks the chain, and without the key (``FLOWFORGE_AUDIT_CHAIN_KEY``,
  or derived from ``FLOWFORGE_SECRET_KEY``) the chain cannot be recomputed. ``verify()`` finds it.
* **Not detected without an external anchor:** deleting the *newest* rows (truncating the tail), or
  replacing the whole chain using a stolen key. Each write logs ``CHAIN seq=... hash=...`` to the
  audit file/stdout stream; ship that to write-once storage and pass ``anchor=`` to ``verify()``.
* **Rows written before this feature (no ``seq``) are "legacy": never verifiable.** They age out
  with the retention window. A forged row with an old timestamp and no ``seq`` is indistinguishable
  from a legacy row.
* Rotating the key makes every existing row fail verification. Set ``FLOWFORGE_AUDIT_CHAIN_KEY`` to a
  fixed value to decouple the chain from ``FLOWFORGE_SECRET_KEY`` rotations.

Two operations legitimately change rows, and both keep the chain verifiable:

* **Retention prune** removes the oldest rows and first appends an ``AUDIT_PRUNED`` row recording the
  hash of the last row removed, so the new head still links to something recorded in the chain.
  Deleting the head *without* that record is reported.
* **GDPR purge** rewrites actor fields of a deleted user's rows. The chain covers a stored
  ``content_digest`` rather than the live columns, so purged rows keep their place; they are flagged
  ``anonymized`` (their content is no longer checked) and an ``AUDIT_ANONYMIZED`` row records how many
  rows were purged. Flagging extra rows to hide an edit is caught by the count not adding up.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy import text

GENESIS = '0' * 64
MAINTENANCE_SETTING = 'flowforge.audit_maintenance'
PRUNED = 'AUDIT_PRUNED'
ANONYMIZED = 'AUDIT_ANONYMIZED'
_LOCK_ID = 0x4646415544495400          # advisory-lock id serialising appends ("FFAUDIT")
_HKDF_INFO = b'flowforge-audit-chain-v1'
_MAX_PROBLEMS = 50


class ChainKeyError(Exception):
    """No usable chain key; rows cannot be sealed or verified."""


class ChainError(Exception):
    """The chain is not in a state this operation can safely continue."""


# -- sealing ------------------------------------------------------------------------------

def chain_key() -> bytes:
    explicit = os.environ.get('FLOWFORGE_AUDIT_CHAIN_KEY', '').strip()
    if explicit:
        try:
            key = bytes.fromhex(explicit)
        except ValueError:
            raise ChainKeyError('FLOWFORGE_AUDIT_CHAIN_KEY must be hex-encoded') from None
        if len(key) < 32:
            raise ChainKeyError('FLOWFORGE_AUDIT_CHAIN_KEY must be at least 32 bytes (64 hex characters)')
        return key
    from flowforge.crypto import _key
    try:
        master = _key()
    except RuntimeError as e:
        raise ChainKeyError(str(e)) from None
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=_HKDF_INFO).derive(master)


def _ts(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime('%Y-%m-%dT%H:%M:%S.%fZ')


def _norm_details(details) -> dict:
    """Round-trip through JSON so what is hashed is exactly what JSONB will hand back."""
    return json.loads(json.dumps(details or {}, default=str))


def content_digest(seq: int, ts: datetime, action: str, username: str, user_id: str | None,
                   ip: str | None, details: dict) -> str:
    blob = json.dumps([seq, _ts(ts), action, username, str(user_id) if user_id else None, ip, details],
                      sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def seal(key: bytes, seq: int, prev_hash: str, digest: str) -> str:
    return hmac.new(key, f'{seq}|{prev_hash}|{digest}'.encode(), hashlib.sha256).hexdigest()


def _lock(conn) -> None:
    conn.execute(text('SELECT pg_advisory_xact_lock(:k)'), {'k': _LOCK_ID})


def _maintenance(conn) -> None:
    """Open the trigger gate for this transaction only."""
    conn.execute(text('SELECT set_config(:s, :v, true)'), {'s': MAINTENANCE_SETTING, 'v': 'on'})


def append(conn, action: str, username: str, user_id: str | None, ip: str | None,
           details: dict | None, ts: datetime | None = None) -> tuple[int, str]:
    """Append a sealed row inside the caller's transaction; returns ``(seq, row_hash)``.

    Takes a transaction-scoped advisory lock, so concurrent writers form one chain. Raises
    :class:`ChainKeyError` before touching the database when there is no key.
    """
    key = chain_key()
    _lock(conn)
    tail = conn.execute(text('SELECT seq, row_hash FROM ff_audit_log WHERE seq IS NOT NULL '
                             'ORDER BY seq DESC LIMIT 1')).first()
    seq, prev = (tail.seq + 1, tail.row_hash) if tail else (1, GENESIS)
    ts = ts or datetime.now(UTC)
    d = _norm_details(details)
    digest = content_digest(seq, ts, action, username, user_id, ip, d)
    row_hash = seal(key, seq, prev, digest)
    conn.execute(text(
        'INSERT INTO ff_audit_log (id, timestamp, action, username, user_id, ip_address, details, '
        'seq, prev_hash, content_digest, row_hash, anonymized) '
        'VALUES (:id, :ts, :action, :username, CAST(:user_id AS UUID), :ip, CAST(:details AS JSONB), '
        ':seq, :prev, :digest, :row_hash, FALSE)'),
        {'id': str(uuid.uuid4()), 'ts': ts, 'action': action, 'username': username,
         'user_id': str(user_id) if user_id else None, 'ip': ip, 'details': json.dumps(d),
         'seq': seq, 'prev': prev, 'digest': digest, 'row_hash': row_hash})
    return seq, row_hash


# -- the two sanctioned modifications -----------------------------------------------------

def prune(conn, cutoff: datetime) -> int:
    """Delete audit rows older than ``cutoff``, leaving a chained checkpoint. Returns rows removed.

    Runs in the caller's transaction (the caller commits). Fails closed: with no key it deletes
    nothing, because it could not record the checkpoint.
    """
    chain_key()
    _maintenance(conn)
    _lock(conn)
    deleted = conn.execute(text('DELETE FROM ff_audit_log WHERE seq IS NULL AND timestamp < :c'),
                           {'c': cutoff}).rowcount or 0                      # legacy rows: nothing to preserve
    tail = conn.execute(text('SELECT max(seq) FROM ff_audit_log WHERE seq IS NOT NULL')).scalar()
    if tail is None:
        return deleted
    keep = conn.execute(text('SELECT min(seq) FROM ff_audit_log WHERE seq IS NOT NULL AND timestamp >= :c'),
                        {'c': cutoff}).scalar()
    through = (keep - 1) if keep is not None else tail
    head = conn.execute(text('SELECT min(seq) FROM ff_audit_log WHERE seq IS NOT NULL')).scalar()
    if head is None or head > through:
        return deleted                                                       # nothing old enough
    through_hash = conn.execute(text('SELECT row_hash FROM ff_audit_log WHERE seq = :s'), {'s': through}).scalar()
    if through_hash is None:
        raise ChainError(f'cannot prune: row {through} is missing (run `flowforge audit verify`)')
    n, anon = conn.execute(text(
        'SELECT count(*), count(*) FILTER (WHERE anonymized) FROM ff_audit_log '
        'WHERE seq IS NOT NULL AND seq <= :t'), {'t': through}).one()
    append(conn, PRUNED, 'system', None, '', {'through_seq': through, 'through_hash': through_hash,
                                              'deleted': n, 'anonymized_removed': anon})
    deleted += conn.execute(text('DELETE FROM ff_audit_log WHERE seq IS NOT NULL AND seq <= :t'),
                            {'t': through}).rowcount or 0
    return deleted


def anonymize_actor(conn, user_id: str, username: str, anon_name: str) -> int:
    """GDPR purge: blank the actor fields of one user's rows, keeping the chain valid.

    Runs in the caller's transaction. Returns the number of rows rewritten.
    """
    _maintenance(conn)
    _lock(conn)
    params = {'uid': str(user_id), 'u': username}
    fresh = conn.execute(text(
        'SELECT count(*) FROM ff_audit_log WHERE (user_id = CAST(:uid AS UUID) OR username = :u) '
        'AND seq IS NOT NULL AND NOT anonymized'), params).scalar()
    changed = conn.execute(text(
        'UPDATE ff_audit_log SET username = :anon, user_id = NULL, ip_address = NULL, anonymized = TRUE '
        'WHERE (user_id = CAST(:uid AS UUID) OR username = :u)'), {**params, 'anon': anon_name}).rowcount or 0
    if fresh:
        actor, actor_id = _actor()
        append(conn, ANONYMIZED, actor, actor_id, '', {'rows': fresh, 'subject': anon_name})
    return changed


def _actor() -> tuple[str, str | None]:
    from flowforge import audit
    uid = audit._current_user_id()
    return audit._current_user(), (None if uid == 'system' else uid)


# -- verification -------------------------------------------------------------------------

@dataclass
class VerifyReport:
    ok: bool = True
    chained_rows: int = 0
    legacy_rows: int = 0
    unchained_after_start: int = 0
    anonymized_rows: int = 0
    first_seq: int | None = None
    last_seq: int | None = None
    tail: str | None = None                  # "seq:hash" - store this somewhere an attacker cannot edit
    anchor_checked: bool = False
    problems: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def problem(self, msg: str) -> None:
        self.ok = False
        if len(self.problems) < _MAX_PROBLEMS:
            self.problems.append(msg)
        elif len(self.problems) == _MAX_PROBLEMS:
            self.problems.append('... further problems not listed')

    def to_dict(self) -> dict:
        return asdict(self)


def _parse_anchor(anchor: str) -> tuple[int, str]:
    seq, _, h = anchor.partition(':')
    if not seq.isdigit() or len(h) != 64 or any(c not in '0123456789abcdef' for c in h):
        raise ValueError('anchor must look like "<seq>:<64 hex chars>" (as logged on the CHAIN line)')
    return int(seq), h


def verify(conn, anchor: str | None = None) -> VerifyReport:
    """Recompute the whole chain and report every inconsistency (up to a cap).

    Streams rows in ``seq`` order, so memory does not grow with the table. ``anchor`` is a
    ``"seq:hash"`` string saved earlier (the ``CHAIN`` line in the audit log, or a previous report's
    ``tail``); it proves the chain still contains that row and has not been cut back past it.
    """
    rep = VerifyReport()
    try:
        key = chain_key()
    except ChainKeyError as e:
        rep.problem(f'cannot verify: {e}')
        return rep
    anchor_seq, anchor_hash = _parse_anchor(anchor) if anchor else (None, None)

    rows = conn.execute(text(
        'SELECT seq, prev_hash, content_digest, row_hash, anonymized, timestamp, action, username, '
        'user_id, ip_address, details FROM ff_audit_log WHERE seq IS NOT NULL ORDER BY seq'
    ).execution_options(stream_results=True, max_row_buffer=5000))
    prev_seq: int | None = None
    prev_hash: str | None = None
    first: tuple[int, str] | None = None
    first_ts = None
    pruned: list[tuple[int, str]] = []
    declared = removed = 0
    anchor_found = None
    for r in rows:
        rep.chained_rows += 1
        if first is None:
            first, first_ts = (r.seq, r.prev_hash), r.timestamp
        elif r.seq != prev_seq + 1:
            rep.problem(f'rows missing or duplicated between seq {prev_seq} and {r.seq}')
        elif r.prev_hash != prev_hash:
            rep.problem(f'seq {r.seq}: prev_hash does not match the previous row (reordered or edited)')
        if seal(key, r.seq, r.prev_hash, r.content_digest) != r.row_hash:
            rep.problem(f'seq {r.seq}: row_hash does not match (row edited, or wrong key)')
        if r.anonymized:
            rep.anonymized_rows += 1
        else:
            actual = content_digest(r.seq, r.timestamp, r.action, r.username, r.user_id, r.ip_address,
                                    _norm_details(r.details))
            if actual != r.content_digest:
                rep.problem(f'seq {r.seq}: contents no longer match what was recorded (action={r.action})')
        if r.action == PRUNED and isinstance(r.details, dict):
            pruned.append((r.details.get('through_seq'), r.details.get('through_hash')))
            removed += int(r.details.get('anonymized_removed') or 0)
        elif r.action == ANONYMIZED and isinstance(r.details, dict):
            declared += int(r.details.get('rows') or 0)
        if anchor_seq is not None and r.seq == anchor_seq:
            anchor_found = r.row_hash
        prev_seq, prev_hash = r.seq, r.row_hash
        rep.last_seq = r.seq
    if first is None:
        rep.notes.append('no chained rows yet')
    else:
        rep.first_seq = first[0]
        rep.tail = f'{prev_seq}:{prev_hash}'
        if first[0] == 1:
            if first[1] != GENESIS:
                rep.problem('seq 1 does not start from the genesis hash')
        elif (first[0] - 1, first[1]) not in pruned:
            rep.problem(f'rows before seq {first[0]} are missing and no retention checkpoint '
                        f'({PRUNED}) accounts for them')
        expected_anon = declared - removed
        if rep.anonymized_rows != expected_anon:
            rep.problem(f'{rep.anonymized_rows} rows are flagged anonymized but the chain records '
                        f'{expected_anon} ({ANONYMIZED} events minus pruned): a flag was added or removed')
        rep.unchained_after_start = conn.execute(text(
            'SELECT count(*) FROM ff_audit_log WHERE seq IS NULL AND timestamp >= :t'), {'t': first_ts}).scalar()
        if rep.unchained_after_start:
            rep.problem(f'{rep.unchained_after_start} rows written after the chain started carry no chain '
                        '(inserted outside the app, or written while no key was available)')
    rep.legacy_rows = conn.execute(text('SELECT count(*) FROM ff_audit_log WHERE seq IS NULL')).scalar() \
        - rep.unchained_after_start
    if rep.legacy_rows:
        rep.notes.append(f'{rep.legacy_rows} rows predate the chain and cannot be verified')
    if anchor_seq is not None:
        rep.anchor_checked = True
        if rep.last_seq is None or rep.last_seq < anchor_seq:
            rep.problem(f'chain ends at seq {rep.last_seq}, before the anchor (seq {anchor_seq}): newest rows were removed')
        elif anchor_found is None:
            if rep.first_seq is not None and anchor_seq < rep.first_seq:
                rep.notes.append(f'anchor seq {anchor_seq} is older than the oldest kept row (pruned by retention); not checked')
                rep.anchor_checked = False
            else:
                rep.problem(f'anchor seq {anchor_seq} is missing from the chain')
        elif anchor_found != anchor_hash:
            rep.problem(f'anchor seq {anchor_seq} exists but its hash differs: that row was rewritten')
    return rep
