"""Optional reversible lookup for subscriber-identifier tokens.

Tokens (flowforge/tokenization.py) are one-way. This module is the opt-in exception: when a step
asks for it (``reconcile`` with ``token_store: true``), the *sampled* identifiers are also written
to ``ff_token_map`` so an authorised admin can turn a finding back into a subscriber without
re-running the audit.

What it is, and is not:

* **A table of personal data.** Treat it like the source systems. The original identifier is stored
  only as AES-GCM ciphertext under ``FLOWFORGE_SECRET_KEY`` (never in the clear, never in logs); the
  token and kind are plain so the table can be searched. Anyone with database access *and* the
  secret key can read it.
* **Small and opt-in.** Only the capped sample of offending keys is stored (at most ``sample_size``
  per category per run, never the whole subscriber base), and only when the step is configured to.
* **Temporary.** Rows are deleted ``FLOWFORGE_TOKEN_MAP_RETENTION_DAYS`` (default 30) after they were
  last seen; ``0`` keeps them forever. The daily maintenance job does the pruning.
* **Reveal is privileged and audited.** ``POST /api/tokens/reveal`` is admin-only and writes a
  ``TOKEN_REVEALED`` audit entry (counts and tokens, never the revealed values).
* **Tied to two keys.** Rotating ``FLOWFORGE_SECRET_KEY`` makes stored ciphertext unreadable (reveal
  reports ``undecryptable``) until a re-encryption tool exists; rotating the tokenization key changes
  all future tokens, so old rows simply stop matching and age out.
"""
from __future__ import annotations

import logging
import os
import re
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)

MAX_REVEAL = 100                       # tokens per reveal request
DEFAULT_RETENTION_DAYS = 30
TOKEN_RE = re.compile(r'^tk_[a-z]+_[0-9a-f]{32}$')


class TokenStoreError(Exception):
    """The mapping could not be read or written (e.g. no application context)."""


def retention_days() -> int:
    """Days a mapping is kept after it was last seen (0 = keep forever)."""
    raw = os.environ.get('FLOWFORGE_TOKEN_MAP_RETENTION_DAYS', str(DEFAULT_RETENTION_DAYS)).strip()
    try:
        return max(0, int(raw))
    except ValueError:
        logger.warning('FLOWFORGE_TOKEN_MAP_RETENTION_DAYS=%r is not a whole number; using %d',
                       raw, DEFAULT_RETENTION_DAYS)
        return DEFAULT_RETENTION_DAYS


def _db():
    try:
        from flask import current_app
        current_app._get_current_object()          # raises outside an application context
    except RuntimeError:
        raise TokenStoreError('the token store needs an application context (run inside the app or a pipeline)') from None
    from flowforge.db.models import TokenMap, db
    return db, TokenMap


def remember_many(items: Iterable[tuple[str, str, str]]) -> int:
    """Store ``(kind, token, original)`` triples; re-seeing a token only refreshes ``last_seen_at``.

    Returns the number of distinct tokens written. Empty originals/tokens are skipped.
    """
    from sqlalchemy.dialects.postgresql import insert

    from flowforge.crypto import encrypt_value
    from flowforge.db.models._shared import _uuid

    distinct: dict[str, tuple[str, str]] = {}
    for kind, token, original in items:
        if token and original:
            distinct.setdefault(token, (kind, original))
    if not distinct:
        return 0
    db, TokenMap = _db()
    now = datetime.now(UTC)
    # explicit ids: a Python-side column default is not applied per row by a multi-row INSERT
    values = [{'id': _uuid(), 'token': t, 'kind': k, 'ciphertext': encrypt_value(o),
               'created_at': now, 'last_seen_at': now}
              for t, (k, o) in distinct.items()]
    stmt = insert(TokenMap).values(values)
    stmt = stmt.on_conflict_do_update(index_elements=['token'], set_={'last_seen_at': now})
    try:
        db.session.execute(stmt)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return len(values)


def reveal(tokens: list[str]) -> dict[str, dict | None]:
    """Map tokens to ``{'kind', 'value'}`` (``None`` when unknown). Never logs a value.

    A row whose ciphertext cannot be decrypted (the secret key changed) comes back as
    ``{'kind', 'value': None, 'error': 'undecryptable'}``.
    """
    from flowforge.crypto import decrypt_value

    if len(tokens) > MAX_REVEAL:
        raise ValueError(f'at most {MAX_REVEAL} tokens per request')
    db, TokenMap = _db()
    out: dict[str, dict | None] = {t: None for t in tokens}
    for row in db.session.query(TokenMap).filter(TokenMap.token.in_(tokens)).all():
        try:
            out[row.token] = {'kind': row.kind, 'value': decrypt_value(row.ciphertext)}
        except Exception:
            out[row.token] = {'kind': row.kind, 'value': None, 'error': 'undecryptable'}
    return out


def purge(older_than_days: int) -> int:
    """Delete mappings not seen for ``older_than_days`` days (``0`` deletes every mapping)."""
    if older_than_days < 0:
        raise ValueError('older_than_days must not be negative')
    db, TokenMap = _db()
    q = db.session.query(TokenMap)
    if older_than_days > 0:
        q = q.filter(TokenMap.last_seen_at < datetime.now(UTC) - timedelta(days=older_than_days))
    deleted = q.delete(synchronize_session=False)
    db.session.commit()
    return deleted
