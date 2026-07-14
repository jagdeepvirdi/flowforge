import tempfile
from pathlib import Path

from flask import Blueprint, jsonify, request

from flowforge.api.auth import require_auth, require_role
from flowforge.api.project_access import ACCESS_DENIED, can_access_project, scope_query
from flowforge.api.validators import validate_email_config
from flowforge.db.models import DEFAULT_PROJECT_ID, EmailConfig, Project, db

bp = Blueprint('emails', __name__)

# ── constants ──
_NOT_FOUND = 'Email config not found'


def _default_project_id() -> str:
    p = db.session.query(Project).filter_by(is_default=True).first()
    return p.id if p else DEFAULT_PROJECT_ID


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
        'body_format': e.body_format,
        'recipient_group_id': e.recipient_group_id,
        'to_addresses': e.to_addresses or [],
        'cc_addresses': e.cc_addresses or [],
        'bcc_addresses': e.bcc_addresses or [],
        'attachment_max_mb': e.attachment_max_mb,
        'drive_folder_id': e.drive_folder_id,
        'drive_share_message': e.drive_share_message,
        'onedrive_folder_id': e.onedrive_folder_id,
        'project_id': e.project_id,
        'created_at': e.created_at.isoformat() if e.created_at else None,
        'updated_at': e.updated_at.isoformat() if e.updated_at else None,
    }


@bp.get('/email-configs')
@require_auth
def list_email_configs():
    query = scope_query(db.session.query(EmailConfig).order_by(EmailConfig.name), EmailConfig.project_id)
    project_id = request.args.get('project_id')
    if project_id:
        if not can_access_project(project_id):
            return jsonify(ACCESS_DENIED), 403
        query = query.filter(EmailConfig.project_id == project_id)
    return jsonify([_email_dict(e) for e in query.all()])


@bp.post('/email-configs')
@require_role(['admin', 'editor'])
def create_email_config():
    data = request.get_json() or {}
    required = ('name', 'subject', 'body_template')
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400
    if data.get('body_format', 'html') not in ('html', 'text'):
        return jsonify({'error': 'body_format must be html or text'}), 400
    err = validate_email_config(data)
    if err:
        return jsonify({'error': err}), 400

    target_project_id = data.get('project_id') or _default_project_id()
    if not can_access_project(target_project_id):
        return jsonify(ACCESS_DENIED), 403

    config = EmailConfig(
        name=data['name'],
        description=data.get('description', ''),
        provider_id=data.get('provider_id'),
        from_name=data.get('from_name'),
        subject=data['subject'],
        header_text=data.get('header_text'),
        body_template=data['body_template'],
        body_format=data.get('body_format', 'html'),
        recipient_group_id=data.get('recipient_group_id'),
        to_addresses=data.get('to_addresses', []),
        cc_addresses=data.get('cc_addresses', []),
        bcc_addresses=data.get('bcc_addresses', []),
        attachment_max_mb=data.get('attachment_max_mb', 10),
        drive_folder_id=data.get('drive_folder_id'),
        drive_share_message=data.get('drive_share_message'),
        onedrive_folder_id=data.get('onedrive_folder_id'),
        project_id=target_project_id,
    )
    db.session.add(config)
    db.session.commit()
    return jsonify(_email_dict(config)), 201


@bp.get('/email-configs/<uuid:config_id>')
@require_auth
def get_email_config(config_id):
    config = db.session.get(EmailConfig, str(config_id))
    if not config:
        return jsonify({'error': _NOT_FOUND}), 404
    if not can_access_project(config.project_id):
        return jsonify(ACCESS_DENIED), 403
    return jsonify(_email_dict(config))


@bp.put('/email-configs/<uuid:config_id>')
@require_role(['admin', 'editor'])
def update_email_config(config_id):
    config = db.session.get(EmailConfig, str(config_id))
    if not config:
        return jsonify({'error': _NOT_FOUND}), 404
    if not can_access_project(config.project_id):
        return jsonify(ACCESS_DENIED), 403

    data = request.get_json() or {}
    if 'body_format' in data and data['body_format'] not in ('html', 'text'):
        return jsonify({'error': 'body_format must be html or text'}), 400
    err = validate_email_config(data)
    if err:
        return jsonify({'error': err}), 400
    if 'project_id' in data and data['project_id'] != config.project_id and not can_access_project(data['project_id']):
        return jsonify(ACCESS_DENIED), 403
    fields = (
        'name', 'description', 'provider_id', 'from_name', 'subject', 'header_text',
        'body_template', 'body_format', 'recipient_group_id', 'to_addresses', 'cc_addresses',
        'bcc_addresses', 'attachment_max_mb', 'drive_folder_id', 'drive_share_message',
        'onedrive_folder_id', 'project_id',
    )
    for field in fields:
        if field in data:
            setattr(config, field, data[field])

    db.session.commit()
    return jsonify(_email_dict(config))


@bp.delete('/email-configs/<uuid:config_id>')
@require_role(['admin', 'editor'])
def delete_email_config(config_id):
    config = db.session.get(EmailConfig, str(config_id))
    if not config:
        return jsonify({'error': _NOT_FOUND}), 404
    if not can_access_project(config.project_id):
        return jsonify(ACCESS_DENIED), 403
    db.session.delete(config)
    db.session.commit()
    return jsonify({'deleted': str(config_id)})


def _unique_email_name(base_name: str, fmt: str = '{base} {n}') -> str:
    candidate = base_name
    n = 1
    while db.session.query(EmailConfig).filter_by(name=candidate).first():
        n += 1
        candidate = fmt.format(base=base_name, n=n)
    return candidate


@bp.post('/email-configs/<uuid:config_id>/clone')
@require_role(['admin', 'editor'])
def clone_email_config(config_id):
    src = db.session.get(EmailConfig, str(config_id))
    if not src:
        return jsonify({'error': _NOT_FOUND}), 404
    if not can_access_project(src.project_id):
        return jsonify(ACCESS_DENIED), 403

    clone = EmailConfig(
        name=_unique_email_name(f'{src.name} (Copy)'),
        description=src.description,
        provider_id=src.provider_id,
        from_name=src.from_name,
        subject=src.subject,
        header_text=src.header_text,
        body_template=src.body_template,
        body_format=src.body_format,
        recipient_group_id=src.recipient_group_id,
        to_addresses=list(src.to_addresses) if src.to_addresses else [],
        cc_addresses=list(src.cc_addresses) if src.cc_addresses else [],
        bcc_addresses=list(src.bcc_addresses) if src.bcc_addresses else [],
        attachment_max_mb=src.attachment_max_mb,
        drive_folder_id=src.drive_folder_id,
        drive_share_message=src.drive_share_message,
        onedrive_folder_id=src.onedrive_folder_id,
        project_id=src.project_id,
    )
    db.session.add(clone)
    db.session.commit()
    return jsonify(_email_dict(clone)), 201


@bp.get('/email-configs/<uuid:config_id>/preview')
@require_auth
def preview_email_config(config_id):
    config = db.session.get(EmailConfig, str(config_id))
    if not config:
        return jsonify({'error': _NOT_FOUND}), 404
    if not can_access_project(config.project_id):
        return jsonify(ACCESS_DENIED), 403

    from flowforge.engine.context import build, render, render_simple_document
    # Build context with sample step results so previews are more realistic
    sample_steps = {
        'report': {
            'output_path': str(Path(tempfile.gettempdir()) / 'sample_report.xlsx'),
            'drive_url': 'https://drive.google.com/open?id=sample',
            'rows_affected': 124,
            'duration_sec': 12.5,
            'rows': [
                {'id': 1, 'name': 'Item A', 'value': 100},
                {'id': 2, 'name': 'Item B', 'value': 200},
            ],
            'table_html': (
                '<table border="1"><thead><tr><th>ID</th><th>Name</th><th>Value</th></tr></thead>'
                '<tbody><tr><td>1</td><td>Item A</td><td>100</td></tr>'
                '<tr><td>2</td><td>Item B</td><td>200</td></tr></tbody></table>'
            ),
            'kv_html': '<dl><dt>ID</dt><dd>1</dd><dt>Name</dt><dd>Item A</dd></dl>',
            'ai_summary': 'The dataset shows a healthy distribution of values with Item B being the highest.',
        }
    }
    ctx = build(pipeline_name='Sample Pipeline', step_results=sample_steps)

    try:
        rendered_subject = render(config.subject or '', ctx)
        if config.body_format == 'text':
            rendered_html = render_simple_document(config.body_template or '', ctx)
        else:
            rendered_html = render(config.body_template or '', ctx)
    except Exception as e:
        return jsonify({'error': f'Template render error: {e}'}), 422

    return jsonify({'subject': rendered_subject, 'html': rendered_html})
