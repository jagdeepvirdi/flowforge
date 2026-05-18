import mimetypes
import os

from flask import Blueprint, jsonify, request, send_file

from flowforge.api.auth import require_auth
from flowforge.db.models import PipelineRun, StepRun, db

bp = Blueprint('runs', __name__)


def _run_dict(r: PipelineRun, include_steps: bool = False) -> dict:
    result = {
        'id': r.id,
        'pipeline_id': r.pipeline_id,
        'pipeline_name': r.pipeline_name,
        'status': r.status,
        'started_at': r.started_at.isoformat() if r.started_at else None,
        'finished_at': r.finished_at.isoformat() if r.finished_at else None,
        'duration_ms': r.duration_ms,
        'triggered_by': r.triggered_by,
        'error_step': r.error_step,
        'error_message': r.error_message,
    }
    if include_steps:
        result['step_runs'] = [_step_run_dict(s) for s in sorted(r.step_runs, key=lambda s: s.step_order)]
    return result


def _step_run_dict(s: StepRun) -> dict:
    return {
        'id': s.id,
        'step_name': s.step_name,
        'step_type': s.step_type,
        'step_order': s.step_order,
        'status': s.status,
        'started_at': s.started_at.isoformat() if s.started_at else None,
        'finished_at': s.finished_at.isoformat() if s.finished_at else None,
        'duration_ms': s.duration_ms,
        'rows_affected': s.rows_affected,
        'output_path': s.output_path,
        'drive_url': s.drive_url,
        'email_sent_to': s.email_sent_to or [],
        'logs': s.logs,
        'error_message': s.error_message,
    }


@bp.get('/runs')
@require_auth
def list_runs():
    query = db.session.query(PipelineRun).order_by(PipelineRun.started_at.desc())

    pipeline_id = request.args.get('pipeline_id')
    status      = request.args.get('status')
    limit       = min(int(request.args.get('limit', 100)), 500)

    if pipeline_id:
        query = query.filter(PipelineRun.pipeline_id == pipeline_id)
    if status:
        query = query.filter(PipelineRun.status == status)

    runs = query.limit(limit).all()
    return jsonify([_run_dict(r) for r in runs])


@bp.get('/runs/<uuid:run_id>')
@require_auth
def get_run(run_id):
    run = db.session.get(PipelineRun, str(run_id))
    if not run:
        return jsonify({'error': 'Run not found'}), 404
    return jsonify(_run_dict(run, include_steps=True))


@bp.get('/step-runs/<uuid:step_run_id>/download')
@require_auth
def download_step_output(step_run_id):
    step_run = db.session.get(StepRun, str(step_run_id))
    if not step_run:
        return jsonify({'error': 'Step run not found'}), 404
    if not step_run.output_path:
        return jsonify({'error': 'No output file for this step'}), 404

    abs_path = os.path.abspath(step_run.output_path)
    if not os.path.isfile(abs_path):
        return jsonify({'error': 'Output file no longer exists on disk'}), 404

    mime, _ = mimetypes.guess_type(abs_path)
    return send_file(
        abs_path,
        mimetype=mime or 'application/octet-stream',
        as_attachment=True,
        download_name=os.path.basename(abs_path),
    )
