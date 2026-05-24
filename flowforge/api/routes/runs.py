import mimetypes
import os
import statistics
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file

from flowforge.api.auth import require_auth
from flowforge.db.models import Pipeline, PipelineRun, StepRun, db

_ANOMALY_MIN_HISTORY = 5
_ANOMALY_THRESHOLD   = 2.0   # z-score


def _check_anomaly(history: list, current) -> dict | None:
    if current is None or len(history) < _ANOMALY_MIN_HISTORY:
        return None
    try:
        mean  = statistics.mean(history)
        stdev = statistics.stdev(history)
    except statistics.StatisticsError:
        return None
    if stdev == 0:
        return None
    z = abs(current - mean) / stdev
    if z < _ANOMALY_THRESHOLD:
        return None
    pct_diff = (current - mean) / mean * 100 if mean != 0 else 0
    return {
        'value':    current,
        'mean':     round(mean, 1),
        'std':      round(stdev, 1),
        'z_score':  round(z, 2),
        'pct_diff': round(pct_diff, 1),
    }

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
    project_id  = request.args.get('project_id')
    status      = request.args.get('status')
    limit       = min(int(request.args.get('limit', 100)), 500)
    offset      = max(int(request.args.get('offset', 0)), 0)

    if pipeline_id:
        query = query.filter(PipelineRun.pipeline_id == pipeline_id)
    if project_id:
        query = (
            query
            .join(Pipeline, PipelineRun.pipeline_id == Pipeline.id)
            .filter(Pipeline.project_id == project_id)
        )
    if status:
        query = query.filter(PipelineRun.status == status)

    runs = query.offset(offset).limit(limit).all()
    return jsonify([_run_dict(r) for r in runs])


@bp.get('/runs/<uuid:run_id>')
@require_auth
def get_run(run_id):
    run = db.session.get(PipelineRun, str(run_id))
    if not run:
        return jsonify({'error': 'Run not found'}), 404
    return jsonify(_run_dict(run, include_steps=True))


@bp.get('/runs/<uuid:run_id>/anomalies')
@require_auth
def get_run_anomalies(run_id):
    """Return statistical anomalies (>2σ) for each step in this run vs its 30-run history."""
    run = db.session.get(PipelineRun, str(run_id))
    if not run:
        return jsonify({'error': 'Run not found'}), 404
    if not run.pipeline_id:
        return jsonify([])

    result = []
    for step in sorted(run.step_runs, key=lambda s: s.step_order):
        history = (
            db.session.query(StepRun)
            .join(PipelineRun, StepRun.pipeline_run_id == PipelineRun.id)
            .filter(
                PipelineRun.pipeline_id == run.pipeline_id,
                StepRun.step_name == step.step_name,
                StepRun.status == 'success',
                PipelineRun.id != str(run_id),
            )
            .order_by(StepRun.started_at.desc())
            .limit(30)
            .all()
        )
        rows_hist = [h.rows_affected for h in history if h.rows_affected is not None]
        dur_hist  = [h.duration_ms   for h in history if h.duration_ms   is not None]

        rows_anomaly = _check_anomaly(rows_hist, step.rows_affected)
        dur_anomaly  = _check_anomaly(dur_hist,  step.duration_ms)

        if rows_anomaly or dur_anomaly:
            result.append({
                'step_id':          step.id,
                'step_name':        step.step_name,
                'rows_anomaly':     rows_anomaly,
                'duration_anomaly': dur_anomaly,
            })

    return jsonify(result)


@bp.get('/step-runs/<uuid:step_run_id>/download')
@require_auth
def download_step_output(step_run_id):
    step_run = db.session.get(StepRun, str(step_run_id))
    if not step_run:
        return jsonify({'error': 'Step run not found'}), 404
    if not step_run.output_path:
        return jsonify({'error': 'No output file for this step'}), 404

    abs_path = Path(step_run.output_path).resolve()
    output_root = Path(os.environ.get('FLOWFORGE_OUTPUT_DIR', 'output')).resolve()
    if not str(abs_path).startswith(str(output_root) + os.sep):
        return jsonify({'error': 'Output file path is not permitted'}), 403
    if not abs_path.is_file():
        return jsonify({'error': 'Output file no longer exists on disk'}), 404

    mime, _ = mimetypes.guess_type(str(abs_path))
    return send_file(
        abs_path,
        mimetype=mime or 'application/octet-stream',
        as_attachment=True,
        download_name=abs_path.name,
    )
