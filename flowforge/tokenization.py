"""Keyed pseudonymisation of subscriber identifiers (MSISDN, IMSI, ...).

A plain or shared-salt hash of an MSISDN/IMSI is brute-forceable (the whole number space
is a few billion values), so it is *not* used. Tokens here are HMAC-SHA256 under a
per-deployment secret: without the key an attacker cannot confirm a guess or enumerate the
space; with it, the same identifier always yields the same token, so findings can still be
joined, de-duplicated and trended, and an analyst can compute the token of a subscriber to
search for them (``tokenize()``).

Properties and limits — keep these honest in docs and sales material:

* Pseudonymisation, not anonymisation: whoever holds the key can confirm a guess, and tokens
  of the same identifier are linkable across runs and exports. Treat the key like any other
  credential.
* One-way by itself: a token cannot be computed back into an identifier. To find a
  subscriber, tokenize their number with the same key and search (``flowforge tokens find``).
  To go from a finding to a subscriber, ``reconcile`` can opt in to ``token_store``, which
  saves the sampled identifiers encrypted in ``ff_token_map`` for an admin to reveal
  (flowforge/token_store.py). That table is personal data; it is off by default.
* Rotating the key changes every token; old and new tokens do not match.
* Normalisation is deliberately minimal: for ``msisdn``/``imsi`` only the digits are kept,
  so ``+1 555 000`` and ``1555000`` match. National-format numbers with a trunk prefix are
  *not* rewritten to E.164 — normalise in the source query if formats are mixed.

The key is ``FLOWFORGE_TOKEN_KEY`` if set (hex, at least 32 bytes), otherwise it is derived
from ``FLOWFORGE_SECRET_KEY`` with HKDF so the tokenization key is never the encryption key.
There is no fallback: a missing key raises :class:`TokenizationError` rather than emitting
raw or unkeyed values.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

TOKEN_KINDS = ('msisdn', 'imsi', 'generic')
_HKDF_INFO = b'flowforge-tokenization-v1'
_TOKEN_HEX_CHARS = 32          # 128 bits: collision-safe for any realistic subscriber base
_DIGITS_ONLY = ('msisdn', 'imsi')


class TokenizationError(Exception):
    """Tokenization is misconfigured (e.g. no key); callers must fail, not fall back to raw values."""


def _derive_key() -> bytes:
    explicit = os.environ.get('FLOWFORGE_TOKEN_KEY', '').strip()
    if explicit:
        try:
            key = bytes.fromhex(explicit)
        except ValueError:
            raise TokenizationError('FLOWFORGE_TOKEN_KEY must be hex-encoded') from None
        if len(key) < 32:
            raise TokenizationError('FLOWFORGE_TOKEN_KEY must be at least 32 bytes (64 hex characters)')
        return key
    if not os.environ.get('FLOWFORGE_SECRET_KEY', '').strip():
        raise TokenizationError(
            'tokenization needs a key: set FLOWFORGE_TOKEN_KEY, or FLOWFORGE_SECRET_KEY to derive one'
        )
    from flowforge.crypto import _key
    try:
        master = _key()
    except RuntimeError as e:
        raise TokenizationError(str(e)) from None
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=_HKDF_INFO).derive(master)


def _normalize(value: object, kind: str) -> str:
    s = str(value).strip()
    if kind in _DIGITS_ONLY:
        s = re.sub(r'\D', '', s)
    return s


def tokenize(value: object, kind: str = 'msisdn') -> str:
    """Return the deterministic token for ``value`` (``''`` for an empty value).

    The kind is mixed into the MAC, so the same digits as an MSISDN and as an IMSI give
    different tokens and cannot be cross-linked.
    """
    if kind not in TOKEN_KINDS:
        raise TokenizationError(f"unknown token kind {kind!r}; use one of: {', '.join(TOKEN_KINDS)}")
    key = _derive_key()
    if value is None:
        return ''
    normalized = _normalize(value, kind)
    if not normalized:
        return ''
    mac = hmac.new(key, kind.encode() + b'\x00' + normalized.encode(), hashlib.sha256)
    return f'tk_{kind}_{mac.hexdigest()[:_TOKEN_HEX_CHARS]}'


def check_ready() -> None:
    """Raise :class:`TokenizationError` now if no usable key exists (fail before doing work)."""
    _derive_key()


_EMAIL_RE = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}')
# 10-15 digit runs (optionally with a leading +) are treated as phone numbers / IMSIs. This
# intentionally over-matches (e.g. a 14-digit timestamp): wrongly scrubbing is the safe side.
_NUMBER_RE = re.compile(r'(?<![\w.])\+?\d{10,15}(?![\w])')


def scrub_text(text: object) -> str:
    """Replace e-mail addresses and phone-/IMSI-like digit runs in free text with tokens.

    For free-text fields (notes, error messages, descriptions) that could carry identifiers
    nobody thought to tokenize. Best effort — it will not catch names, addresses or numbers
    split by spaces or punctuation. It does not make arbitrary text safe to export.
    """
    if text is None:
        return ''
    s = str(text)
    s = _EMAIL_RE.sub(lambda m: tokenize(m.group(0).lower(), 'generic'), s)
    return _NUMBER_RE.sub(lambda m: tokenize(m.group(0), 'msisdn'), s)
