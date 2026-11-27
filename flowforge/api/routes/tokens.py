"""Reveal the subscriber identifiers behind tokens (admin only, audited)."""
from flask import Blueprint, jsonify, request

from flowforge import audit, token_store
from flowforge.api.auth import require_role

bp = Blueprint('tokens', __name__)


@bp.post('/tokens/reveal')
@require_role('admin')
def reveal_tokens():
    """Body: ``{"tokens": ["tk_msisdn_...", ...]}`` (1 to 100). Returns ``{"results": {token: {kind, value} | null}}``.

    This hands out personal data: it is admin-only, the response is not cacheable, and every call
    is recorded as TOKEN_REVEALED (who, how many, which tokens - not the values).
    """
    data = request.get_json(silent=True) or {}
    tokens = data.get('tokens')
    if not isinstance(tokens, list) or not tokens or not all(isinstance(t, str) for t in tokens):
        return jsonify({'error': 'tokens must be a non-empty list of strings'}), 400
    tokens = list(dict.fromkeys(t.strip() for t in tokens))
    if len(tokens) > token_store.MAX_REVEAL:
        return jsonify({'error': f'at most {token_store.MAX_REVEAL} tokens per request'}), 400
    bad = [t for t in tokens if not token_store.TOKEN_RE.match(t)]
    if bad:
        return jsonify({'error': f'{len(bad)} value(s) are not tokens (expected tk_<kind>_<32 hex>)'}), 400

    results = token_store.reveal(tokens)
    found = sum(1 for v in results.values() if v and v.get('value') is not None)
    audit.log_token_reveal(len(tokens), found, tokens, request.remote_addr or '')
    resp = jsonify({'results': results})
    resp.headers['Cache-Control'] = 'no-store'
    return resp
