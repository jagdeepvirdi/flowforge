from flask import Blueprint, jsonify, request

from flowforge.api.auth import require_auth
from flowforge.api.validators import validate_report
from flowforge.db.models import DEFAULT_PROJECT_ID, Project, ReportConfig, db

bp = Blueprint('reports', __name__)


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
        'project_id': r.project_id,
        'created_at': r.created_at.isoformat() if r.created_at else None,
        'updated_at': r.updated_at.isoformat() if r.updated_at else None,
    }


@bp.get('/report-configs')
@require_auth
def list_report_configs():
    query = db.session.query(ReportConfig).order_by(ReportConfig.name)
    project_id = request.args.get('project_id')
    if project_id:
        query = query.filter(ReportConfig.project_id == project_id)
    return jsonify([_report_dict(r) for r in query.all()])


@bp.post('/report-configs')
@require_auth
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
        project_id=data.get('project_id') or _default_project_id(),
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
    return jsonify(_report_dict(config))


@bp.put('/report-configs/<uuid:config_id>')
@require_auth
def update_report_config(config_id):
    config = db.session.get(ReportConfig, str(config_id))
    if not config:
        return jsonify({'error': 'Report config not found'}), 404

    data = request.get_json() or {}
    err = validate_report(data)
    if err:
        return jsonify({'error': err}), 400
    fields = ('name', 'description', 'connection_id', 'query', 'format',
              'template_path', 'output_filename', 'title', 'sheet_name', 'columns', 'project_id')
    for field in fields:
        if field in data:
            setattr(config, field, data[field])

    db.session.commit()
    return jsonify(_report_dict(config))


@bp.delete('/report-configs/<uuid:config_id>')
@require_auth
def delete_report_config(config_id):
    config = db.session.get(ReportConfig, str(config_id))
    if not config:
        return jsonify({'error': 'Report config not found'}), 404
    db.session.delete(config)
    db.session.commit()
    return jsonify({'deleted': str(config_id)})


@bp.post('/report-configs/<uuid:config_id>/preview')
@require_auth
def preview_report(config_id):
    """Run the report query and return the first 20 rows for UI preview."""
    config = db.session.get(ReportConfig, str(config_id))
    if not config:
        return jsonify({'error': 'Report config not found'}), 404
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
    except Exception as e:
        return jsonify({'error': str(e)}), 500
