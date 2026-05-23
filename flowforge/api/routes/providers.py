from flask import Blueprint, jsonify, request

import flowforge.audit as audit
from flowforge.api.auth import require_auth
from flowforge.crypto import decrypt_config, encrypt_config
from flowforge.db.models import EmailProvider, db

bp = Blueprint('providers', __name__)

_SENSITIVE = {'password', 'secret', 'token', 'key', 'refresh_token', 'client_secret'}


def _provider_dict(p: EmailProvider, include_config: bool = False) -> dict:
    result = {
        'id': p.id,
        'name': p.name,
        'provider_type': p.provider_type,
        'is_default': p.is_default,
        'created_at': p.created_at.isoformat() if p.created_at else None,
    }
    if include_config:
        cfg = decrypt_config(p.config)
        result['config'] = {
            k: '***' if any(s in k.lower() for s in _SENSITIVE) else v
            for k, v in cfg.items()
        }
    return result


@bp.get('/email-providers')
@require_auth
def list_providers():
    providers = db.session.query(EmailProvider).order_by(EmailProvider.name).all()
    return jsonify([_provider_dict(p) for p in providers])


@bp.post('/email-providers')
@require_auth
def create_provider():
    data = request.get_json() or {}
    if not data.get('name'):
        return jsonify({'error': 'name is required'}), 400
    if data.get('provider_type') not in ('gmail', 'microsoft365', 'smtp'):
        return jsonify({'error': 'provider_type must be gmail, microsoft365, or smtp'}), 400
    if not data.get('config'):
        return jsonify({'error': 'config is required'}), 400

    provider = EmailProvider(
        name=data['name'],
        provider_type=data['provider_type'],
        config=encrypt_config(data['config']),
        is_default=data.get('is_default', False),
    )
    db.session.add(provider)
    db.session.commit()
    audit.log_provider_change('CREATED', provider.name, provider.id)
    return jsonify(_provider_dict(provider)), 201


@bp.get('/email-providers/<uuid:provider_id>')
@require_auth
def get_provider(provider_id):
    provider = db.session.get(EmailProvider, str(provider_id))
    if not provider:
        return jsonify({'error': 'Provider not found'}), 404
    return jsonify(_provider_dict(provider, include_config=True))


@bp.put('/email-providers/<uuid:provider_id>')
@require_auth
def update_provider(provider_id):
    provider = db.session.get(EmailProvider, str(provider_id))
    if not provider:
        return jsonify({'error': 'Provider not found'}), 404

    data = request.get_json() or {}
    if 'name' in data:
        provider.name = data['name']
    if 'is_default' in data:
        provider.is_default = data['is_default']
    if 'config' in data:
        existing = decrypt_config(provider.config)
        for k, v in data['config'].items():
            if v != '***':
                existing[k] = v
        provider.config = encrypt_config(existing)

    db.session.commit()
    audit.log_provider_change('UPDATED', provider.name, provider.id)
    return jsonify(_provider_dict(provider, include_config=True))


@bp.delete('/email-providers/<uuid:provider_id>')
@require_auth
def delete_provider(provider_id):
    provider = db.session.get(EmailProvider, str(provider_id))
    if not provider:
        return jsonify({'error': 'Provider not found'}), 404
    name, pid = provider.name, provider.id
    db.session.delete(provider)
    db.session.commit()
    audit.log_provider_change('DELETED', name, pid)
    return jsonify({'deleted': str(provider_id)})


@bp.post('/email-providers/<uuid:provider_id>/test')
@require_auth
def test_provider(provider_id):
    from flowforge.email_providers.factory import get_email_provider
    try:
        provider = get_email_provider(str(provider_id))
        ok, msg = provider.test()
        if ok:
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': msg}), 502
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 502
