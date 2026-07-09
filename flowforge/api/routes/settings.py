"""Instance-wide operational settings (currently: data retention overrides)."""
from flask import Blueprint, g, jsonify, request

import flowforge.audit as audit
from flowforge.api.auth import require_auth, require_role
from flowforge.db.models import SystemSettings, db
from flowforge.engine.settings import (
    get_audit_retention_days,
    get_output_ttl_days,
    get_run_retention_days,
)

bp = Blueprint('settings', __name__)

_FIELDS = ('run_retention_days', 'audit_retention_days', 'output_ttl_days')


def _effective_values() -> dict:
    return {
        'run_retention_days':   get_run_retention_days(),
        'audit_retention_days': get_audit_retention_days(),
        'output_ttl_days':      get_output_ttl_days(),
    }


@bp.get('/settings/retention')
@require_auth
def get_retention_settings():
    row = db.session.get(SystemSettings, 1)
    return jsonify({
        **_effective_values(),
        'is_custom': {
            field: bool(row is not None and getattr(row, field) is not None)
            for field in _FIELDS
        },
    })


@bp.put('/settings/retention')
@require_role('admin')
def update_retention_settings():
    data = request.get_json() or {}
    unknown = set(data.keys()) - set(_FIELDS)
    if unknown:
        return jsonify({'error': f'Unknown field(s): {", ".join(sorted(unknown))}'}), 400

    updates: dict = {}
    for field in _FIELDS:
        if field not in data:
            continue
        value = data[field]
        if value is None:
            updates[field] = None
            continue
        if not isinstance(value, int) or isinstance(value, bool):
            return jsonify({'error': f'{field} must be an integer or null'}), 400
        if field == 'output_ttl_days':
            if value < 1:
                return jsonify({'error': (
                    'output_ttl_days must be at least 1 — 0 would delete every output '
                    'file immediately. Use `flowforge cleanup --days 0` if you '
                    'intentionally need that; it requires explicit confirmation.'
                )}), 400
        elif value < 0:
            return jsonify({'error': f'{field} must be 0 (keep forever) or a positive integer'}), 400
        updates[field] = value

    if not updates:
        return jsonify({'error': 'No valid fields provided'}), 400

    row = db.session.get(SystemSettings, 1)
    if row is None:
        row = SystemSettings(id=1)
        db.session.add(row)

    for field, value in updates.items():
        setattr(row, field, value)
    row.updated_by = g.user_token.get('sub', 'system')

    db.session.commit()
    audit.log_settings_change(updates)

    return jsonify(_effective_values())
