from flask import Blueprint, jsonify, request

from flowforge.api.auth import require_auth
from flowforge.db.models import EmailConfig, db

bp = Blueprint('emails', __name__)


def _email_dict(e: EmailConfig) -> dict:
    return {
        'id': e.id,
        'name': e.name,
        'description': e.description,
        'provider_id': e.provider_id,
        'from_name': e.from_name,
        'subject': e.subject,
        'header_text': e.header_text,
        'body_template': e.body_template,
        'recipient_group_id': e.recipient_group_id,
        'to_addresses': e.to_addresses or [],
        'cc_addresses': e.cc_addresses or [],
        'bcc_addresses': e.bcc_addresses or [],
        'attachment_max_mb': e.attachment_max_mb,
        'drive_folder_id': e.drive_folder_id,
        'drive_share_message': e.drive_share_message,
        'created_at': e.created_at.isoformat() if e.created_at else None,
        'updated_at': e.updated_at.isoformat() if e.updated_at else None,
    }


@bp.get('/email-configs')
@require_auth
def list_email_configs():
    configs = db.session.query(EmailConfig).order_by(EmailConfig.name).all()
    return jsonify([_email_dict(e) for e in configs])


@bp.post('/email-configs')
@require_auth
def create_email_config():
    data = request.get_json() or {}
    required = ('name', 'subject', 'body_template')
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

    config = EmailConfig(
        name=data['name'],
        description=data.get('description', ''),
        provider_id=data.get('provider_id'),
        from_name=data.get('from_name'),
        subject=data['subject'],
        header_text=data.get('header_text'),
        body_template=data['body_template'],
        recipient_group_id=data.get('recipient_group_id'),
        to_addresses=data.get('to_addresses', []),
        cc_addresses=data.get('cc_addresses', []),
        bcc_addresses=data.get('bcc_addresses', []),
        attachment_max_mb=data.get('attachment_max_mb', 10),
        drive_folder_id=data.get('drive_folder_id'),
        drive_share_message=data.get('drive_share_message'),
    )
    db.session.add(config)
    db.session.commit()
    return jsonify(_email_dict(config)), 201


@bp.get('/email-configs/<uuid:config_id>')
@require_auth
def get_email_config(config_id):
    config = db.session.get(EmailConfig, str(config_id))
    if not config:
        return jsonify({'error': 'Email config not found'}), 404
    return jsonify(_email_dict(config))


@bp.put('/email-configs/<uuid:config_id>')
@require_auth
def update_email_config(config_id):
    config = db.session.get(EmailConfig, str(config_id))
    if not config:
        return jsonify({'error': 'Email config not found'}), 404

    data = request.get_json() or {}
    fields = (
        'name', 'description', 'provider_id', 'from_name', 'subject', 'header_text',
        'body_template', 'recipient_group_id', 'to_addresses', 'cc_addresses',
        'bcc_addresses', 'attachment_max_mb', 'drive_folder_id', 'drive_share_message',
    )
    for field in fields:
        if field in data:
            setattr(config, field, data[field])

    db.session.commit()
    return jsonify(_email_dict(config))


@bp.delete('/email-configs/<uuid:config_id>')
@require_auth
def delete_email_config(config_id):
    config = db.session.get(EmailConfig, str(config_id))
    if not config:
        return jsonify({'error': 'Email config not found'}), 404
    db.session.delete(config)
    db.session.commit()
    return jsonify({'deleted': str(config_id)})
