import logging

from flask import Blueprint, jsonify, request

import flowforge.audit as audit
from flowforge.api.app import limiter
from flowforge.api.auth import require_auth, require_role
from flowforge.api.project_access import ACCESS_DENIED, can_access_project, scope_query
from flowforge.api.validators import validate_report
from flowforge.db.models import DEFAULT_PROJECT_ID, Project, ReportConfig, db

bp = Blueprint('reports', __name__)
logger = logging.getLogger(__name__)


def _default_project_id() -> str:
    p = db.session.query(Project).filter_by(is_default=True).first()
    return p.id if p else DEFAULT_PROJECT_ID


def _report_dict(r: ReportConfig) -> dict:
    return {
        'id': r.id,
        'name': r.name,
        'description': r.description,
        'connection_id': r.connection_id,
        'query': r.query,
        'format': r.format,
        'template_path': r.template_path,
        'output_filename': r.output_filename,
        'title': r.title,
        'sheet_name': r.sheet_name,
        'columns': r.columns or [],
        'column_formatting': r.column_formatting or [],
        'project_id': r.project_id,
        'created_at': r.created_at.isoformat() if r.created_at else None,
        'updated_at': r.updated_at.isoformat() if r.updated_at else None,
    }


@bp.get('/report-configs')
@require_auth
def list_report_configs():
    query = scope_query(db.session.query(ReportConfig).order_by(ReportConfig.name), ReportConfig.project_id)
    project_id = request.args.get('project_id')
    if project_id:
        if not can_access_project(project_id):
            return jsonify(ACCESS_DENIED), 403
        query = query.filter(ReportConfig.project_id == project_id)
    return jsonify([_report_dict(r) for r in query.all()])


@bp.post('/report-configs')
@require_role(['admin', 'editor'])
def create_report_config():
    data = request.get_json() or {}
    required = ('name', 'query', 'format', 'output_filename')
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400
    if data['format'] not in ('excel', 'csv', 'pdf', 'json'):
        return jsonify({'error': 'format must be excel, csv, pdf, or json'}), 400
    err = validate_report(data)
    if err:
        return jsonify({'error': err}), 400

    target_project_id = data.get('project_id') or _default_project_id()
    if not can_access_project(target_project_id):
        return jsonify(ACCESS_DENIED), 403

    config = ReportConfig(
        name=data['name'],
        description=data.get('description', ''),
        connection_id=data.get('connection_id'),
        query=data['query'],
        format=data['format'],
        template_path=data.get('template_path'),
        output_filename=data['output_filename'],
        title=data.get('title'),
        sheet_name=data.get('sheet_name'),
        columns=data.get('columns'),
        column_formatting=data.get('column_formatting') or [],
        project_id=target_project_id,
    )
    db.session.add(config)
    db.session.commit()
    return jsonify(_report_dict(config)), 201


@bp.get('/report-configs/<uuid:config_id>')
@require_auth
def get_report_config(config_id):
    config = db.session.get(ReportConfig, str(config_id))
    if not config:
        return jsonify({'error': 'Report config not found'}), 404
    if not can_access_project(config.project_id):
        return jsonify(ACCESS_DENIED), 403
    return jsonify(_report_dict(config))


@bp.put('/report-configs/<uuid:config_id>')
@require_role(['admin', 'editor'])
def update_report_config(config_id):
    config = db.session.get(ReportConfig, str(config_id))
    if not config:
        return jsonify({'error': 'Report config not found'}), 404
    if not can_access_project(config.project_id):
        return jsonify(ACCESS_DENIED), 403

    data = request.get_json() or {}
    err = validate_report(data)
    if err:
        return jsonify({'error': err}), 400
    if 'project_id' in data and data['project_id'] != config.project_id and not can_access_project(data['project_id']):
        return jsonify(ACCESS_DENIED), 403
    fields = ('name', 'description', 'connection_id', 'query', 'format',
              'template_path', 'output_filename', 'title', 'sheet_name', 'columns',
              'column_formatting', 'project_id')
    for field in fields:
        if field in data:
            setattr(config, field, data[field])

    db.session.commit()
    audit.log_report_change('UPDATED', config.name, config.id)
    return jsonify(_report_dict(config))


@bp.delete('/report-configs/<uuid:config_id>')
@require_role(['admin', 'editor'])
def delete_report_config(config_id):
    config = db.session.get(ReportConfig, str(config_id))
    if not config:
        return jsonify({'error': 'Report config not found'}), 404
    if not can_access_project(config.project_id):
        return jsonify(ACCESS_DENIED), 403
    db.session.delete(config)
    db.session.commit()
    return jsonify({'deleted': str(config_id)})


def _unique_report_name(base_name: str, fmt: str = '{base} {n}') -> str:
    candidate = base_name
    n = 1
    while db.session.query(ReportConfig).filter_by(name=candidate).first():
        n += 1
        candidate = fmt.format(base=base_name, n=n)
    return candidate


@bp.post('/report-configs/<uuid:config_id>/clone')
@require_role(['admin', 'editor'])
def clone_report_config(config_id):
    src = db.session.get(ReportConfig, str(config_id))
    if not src:
        return jsonify({'error': 'Report config not found'}), 404
    if not can_access_project(src.project_id):
        return jsonify(ACCESS_DENIED), 403

    clone = ReportConfig(
        name=_unique_report_name(f'{src.name} (Copy)'),
        description=src.description,
        connection_id=src.connection_id,
        query=src.query,
        format=src.format,
        template_path=src.template_path,
        output_filename=src.output_filename,
        title=src.title,
        sheet_name=src.sheet_name,
        columns=list(src.columns) if src.columns else None,
        column_formatting=list(src.column_formatting) if src.column_formatting else [],
        project_id=src.project_id,
    )
    db.session.add(clone)
    db.session.commit()
    audit.log_report_change('CLONED', clone.name, clone.id)
    return jsonify(_report_dict(clone)), 201


@bp.post('/report-configs/<uuid:config_id>/preview')
@require_auth
@limiter.limit('20 per minute')
def preview_report(config_id):
    """Run the report query and return the first 20 rows for UI preview."""
    config = db.session.get(ReportConfig, str(config_id))
    if not config:
        return jsonify({'error': 'Report config not found'}), 404
    if not can_access_project(config.project_id):
        return jsonify(ACCESS_DENIED), 403
    if not config.connection_id:
        return jsonify({'error': 'No database connection configured'}), 400

    from flowforge.connections.factory import get_connection
    from flowforge.engine.context import build, render

    ctx = build('preview')
    sql = render(config.query, ctx)

    try:
        with get_connection(config.connection_id) as conn:
            rows = conn.execute_query(sql.rstrip().rstrip(';') + ' LIMIT 20')
        columns = config.columns or [f'col{i}' for i in range(len(rows[0]))] if rows else []
        return jsonify({'columns': columns, 'rows': [list(r) for r in rows]})
    except Exception:  # pragma: no cover
        logger.exception('report preview query failed for config %s', config_id)
        return jsonify({'error': 'Query failed. Check server logs for details.'}), 500
