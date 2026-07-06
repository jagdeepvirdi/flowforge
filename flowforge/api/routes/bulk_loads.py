from flask import Blueprint, jsonify, request

import flowforge.audit as audit
from flowforge.api.auth import require_auth
from flowforge.db.models import BulkLoadConfig, db
from flowforge.steps.bulk_load import preview_bulk_load

bp = Blueprint('bulk_loads', __name__)

# ── constants ──
_NOT_FOUND = 'Bulk load config not found'


def _cfg_dict(c: BulkLoadConfig) -> dict:
    return {
        'id':                  c.id,
        'name':                c.name,
        'description':         c.description,
        'connection_id':       c.connection_id,
        'source_directory':    c.source_directory,
        'file_prefix':         c.file_prefix or '',
        'file_prefix_exclude': c.file_prefix_exclude or '',
        'file_type':           c.file_type or 'csv',
        'delimiter':           c.delimiter or ',',
        'header_rows':         c.header_rows if c.header_rows is not None else 1,
        'footer_rows':         c.footer_rows if c.footer_rows is not None else 0,
        'target_table':        c.target_table,
        'load_mode':           c.load_mode or 'append',
        'column_mapping':      c.column_mapping or [],
        'use_sqlloader':       bool(c.use_sqlloader),
        'archive_directory':   c.archive_directory or '',
        'on_no_files':         c.on_no_files or 'skip',
        'created_at':          c.created_at.isoformat() if c.created_at else None,
        'updated_at':          c.updated_at.isoformat() if c.updated_at else None,
    }


@bp.get('/bulk-load-configs')
@require_auth
def list_bulk_load_configs():
    configs = db.session.query(BulkLoadConfig).order_by(BulkLoadConfig.name).all()
    return jsonify([_cfg_dict(c) for c in configs])


@bp.post('/bulk-load-configs')
@require_auth
def create_bulk_load_config():
    data = request.get_json() or {}
    for field in ('name', 'source_directory', 'target_table'):
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    cfg = BulkLoadConfig(
        name=data['name'],
        description=data.get('description', ''),
        connection_id=data.get('connection_id') or None,
        source_directory=data['source_directory'],
        file_prefix=data.get('file_prefix', ''),
        file_prefix_exclude=data.get('file_prefix_exclude', ''),
        file_type=data.get('file_type', 'csv'),
        delimiter=data.get('delimiter', ','),
        header_rows=int(data.get('header_rows', 1)),
        footer_rows=int(data.get('footer_rows', 0)),
        target_table=data['target_table'],
        load_mode=data.get('load_mode', 'append'),
        column_mapping=data.get('column_mapping', []),
        use_sqlloader=bool(data.get('use_sqlloader', False)),
        archive_directory=data.get('archive_directory', ''),
        on_no_files=data.get('on_no_files', 'skip'),
    )
    db.session.add(cfg)
    db.session.commit()
    return jsonify(_cfg_dict(cfg)), 201


@bp.get('/bulk-load-configs/<uuid:config_id>')
@require_auth
def get_bulk_load_config(config_id):
    cfg = db.session.get(BulkLoadConfig, str(config_id))
    if not cfg:
        return jsonify({'error': _NOT_FOUND}), 404
    return jsonify(_cfg_dict(cfg))


@bp.put('/bulk-load-configs/<uuid:config_id>')
@require_auth
def update_bulk_load_config(config_id):
    cfg = db.session.get(BulkLoadConfig, str(config_id))
    if not cfg:
        return jsonify({'error': _NOT_FOUND}), 404

    data = request.get_json() or {}
    fields = (
        'name', 'description', 'connection_id', 'source_directory',
        'file_prefix', 'file_prefix_exclude', 'file_type', 'delimiter',
        'header_rows', 'footer_rows', 'target_table', 'load_mode',
        'column_mapping', 'use_sqlloader', 'archive_directory', 'on_no_files',
    )
    for field in fields:
        if field in data:
            value = data[field]
            if field == 'connection_id':
                value = value or None
            setattr(cfg, field, value)

    db.session.commit()
    audit.log_bulk_load_change('UPDATED', cfg.name, cfg.id)
    return jsonify(_cfg_dict(cfg))


@bp.delete('/bulk-load-configs/<uuid:config_id>')
@require_auth
def delete_bulk_load_config(config_id):
    cfg = db.session.get(BulkLoadConfig, str(config_id))
    if not cfg:
        return jsonify({'error': _NOT_FOUND}), 404
    db.session.delete(cfg)
    db.session.commit()
    return jsonify({'deleted': str(config_id)})


@bp.post('/bulk-load-configs/<uuid:config_id>/validate')
@require_auth
def validate_bulk_load_config(config_id):
    """Preview the first matching source file without loading any data.

    Optional JSON body {"dry_run": true} also attempts a rolled-back INSERT
    of the sampled rows against the real target table (see preview_bulk_load).
    """
    cfg = db.session.get(BulkLoadConfig, str(config_id))
    if not cfg:
        return jsonify({'error': _NOT_FOUND}), 404
    body = request.get_json(silent=True) or {}
    dry_run = bool(body.get('dry_run', False))
    try:
        result = preview_bulk_load(_cfg_dict(cfg), dry_run=dry_run)
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@bp.post('/bulk-load-configs/validate-raw')
@require_auth
def validate_bulk_load_config_raw():
    """Preview the first matching source file for an unsaved (in-progress) config.

    Optional `dry_run: true` in the body also attempts a rolled-back INSERT
    of the sampled rows against the real target table (see preview_bulk_load).
    """
    data = request.get_json() or {}
    dry_run = bool(data.pop('dry_run', False))
    try:
        result = preview_bulk_load(data, dry_run=dry_run)
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
