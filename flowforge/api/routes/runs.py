import mimetypes
import os
import statistics
from collections import defaultdict
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file

from flowforge.api.auth import require_auth, require_role
from flowforge.api.serializers import run_dict, step_run_dict
from flowforge.db.models import Pipeline, PipelineRun, db

# ── constants ──
_NOT_FOUND = 'Run not found'

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

_DASHBOARD_BARS = 14  # number of recent runs returned per pipeline


@bp.get('/dashboard/summary')
@require_auth
def dashboard_summary():
    """Return the last _DASHBOARD_BARS runs for every pipeline in a single query.

    Returns: { "pipeline_runs": { "<pipeline_id>": [run, ...] } }
    """
    project_id = request.args.get('project_id')

    pipeline_q = db.session.query(Pipeline.id)
    if project_id:
        pipeline_q = pipeline_q.filter(Pipeline.project_id == project_id)
    pipeline_ids = [row.id for row in pipeline_q.all()]

    if not pipeline_ids:
        return jsonify({'pipeline_runs': {}})

    all_runs = (
        db.session.query(PipelineRun)
        .filter(PipelineRun.pipeline_id.in_(pipeline_ids))
        .order_by(PipelineRun.pipeline_id, PipelineRun.started_at.desc())
        .all()
    )

    grouped: dict[str, list] = defaultdict(list)
    for r in all_runs:
        pid = r.pipeline_id
        if len(grouped[pid]) < _DASHBOARD_BARS:
            grouped[pid].append(run_dict(r))

    return jsonify({'pipeline_runs': dict(grouped)})


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
    return jsonify([run_dict(r) for r in runs])


@bp.get('/runs/<uuid:run_id>')
@require_auth
def get_run(run_id):
    run = db.session.get(PipelineRun, str(run_id))
    if not run:
        return jsonify({'error': _NOT_FOUND}), 404
    return jsonify(run_dict(run, include_steps=True))


@bp.get('/runs/<uuid:run_id>/anomalies')
@require_auth
def get_run_anomalies(run_id):
    """Return statistical anomalies (>2σ) for each step in this run vs its 30-run history."""
    run = db.session.get(PipelineRun, str(run_id))
    if not run:
        return jsonify({'error': _NOT_FOUND}), 404
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


@bp.post('/runs/<uuid:run_id>/cancel')
@require_role(['admin', 'editor'])
def cancel_run(run_id):
    from datetime import datetime, timezone
    run = db.session.get(PipelineRun, str(run_id))
    if not run:
        return jsonify({'error': _NOT_FOUND}), 404
    if run.status not in ('running', 'pending'):
        return jsonify({'error': f'Cannot cancel a run with status {run.status!r}'}), 409
    run.status = 'cancelled'
    run.finished_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({'message': 'Run cancelled', 'run_id': str(run_id)})
