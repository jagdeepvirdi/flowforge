import csv
import io
import mimetypes
import os
import statistics
from collections import defaultdict
from datetime import UTC
from pathlib import Path

from flask import Blueprint, Response, jsonify, request, send_file

from flowforge.api.auth import require_auth, require_role
from flowforge.api.serializers import run_dict
from flowforge.db.models import Pipeline, PipelineRun, StepRun, db

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


@bp.get('/runs/export')
@require_auth
def export_runs():
    """Export pipeline runs as CSV"""
    format_type = request.args.get('format', 'csv')
    if format_type.lower() != 'csv':
        return jsonify({'error': 'Only CSV format is supported'}), 400

    try:
        limit = min(int(request.args.get('limit', 10_000)), 10_000)
    except ValueError:
        return jsonify({'error': 'limit must be an integer'}), 400

    query = db.session.query(PipelineRun).order_by(PipelineRun.started_at.desc())

    pipeline_id = request.args.get('pipeline_id')
    project_id  = request.args.get('project_id')
    status      = request.args.get('status')

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

    runs = query.limit(limit).all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Pipeline Name',
        'Run ID',
        'Status',
        'Triggered By',
        'Started At',
        'Finished At',
        'Duration (ms)',
        'Error Message'
    ])
    
    # Write data rows
    for run in runs:
        writer.writerow([
            run.pipeline_name,
            str(run.id),
            run.status,
            run.triggered_by or '',
            run.started_at.isoformat() if run.started_at else '',
            run.finished_at.isoformat() if run.finished_at else '',
            run.duration_ms or '',
            run.error_message or ''
        ])
    
    # Return CSV response
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename=run_history.csv'
        }
    )


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


@bp.get('/runs/<uuid:run_id>/diff')
@require_auth
def get_run_diff(run_id):
    """Compare this run's step metrics vs the previous successful run of the same pipeline."""
    import os
    from pathlib import Path as _Path

    run = db.session.get(PipelineRun, str(run_id))
    if not run:
        return jsonify({'error': _NOT_FOUND}), 404
    if not run.pipeline_id:
        return jsonify({'prev_run_id': None, 'steps': []})

    prev_run = (
        db.session.query(PipelineRun)
        .filter(
            PipelineRun.pipeline_id == run.pipeline_id,
            PipelineRun.status == 'success',
            PipelineRun.id != str(run_id),
            PipelineRun.started_at < run.started_at,
        )
        .order_by(PipelineRun.started_at.desc())
        .first()
    )

    if not prev_run:
        return jsonify({'prev_run_id': None, 'steps': []})

    prev_steps = {s.step_name: s for s in prev_run.step_runs}
    output_root = _Path(os.environ.get('FLOWFORGE_OUTPUT_DIR', 'output')).resolve()

    def _file_size(path_str: str | None) -> int | None:
        if not path_str:
            return None
        try:
            p = _Path(path_str).resolve()
            if str(p).startswith(str(output_root)) and p.is_file():
                return p.stat().st_size
        except Exception:  # nosec B110 — best-effort file size lookup
            pass
        return None

    result = []
    for step in sorted(run.step_runs, key=lambda s: s.step_order):
        prev = prev_steps.get(step.step_name)

        rows_delta = None
        if step.rows_affected is not None and prev and prev.rows_affected is not None:
            rows_delta = step.rows_affected - prev.rows_affected

        dur_delta_pct = None
        if step.duration_ms and prev and prev.duration_ms:
            dur_delta_pct = round(
                (step.duration_ms - prev.duration_ms) / prev.duration_ms * 100, 1
            )

        size_curr = _file_size(step.output_path)
        size_prev = _file_size(prev.output_path if prev else None)
        size_delta = (size_curr - size_prev) if (size_curr is not None and size_prev is not None) else None

        result.append({
            'step_name':         step.step_name,
            'step_type':         step.step_type,
            'step_order':        step.step_order,
            'is_new_step':       prev is None,
            'rows_current':      step.rows_affected,
            'rows_prev':         prev.rows_affected if prev else None,
            'rows_delta':        rows_delta,
            'duration_current':  step.duration_ms,
            'duration_prev':     prev.duration_ms if prev else None,
            'duration_delta_pct': dur_delta_pct,
            'size_current':      size_curr,
            'size_prev':         size_prev,
            'size_delta':        size_delta,
        })

    return jsonify({'prev_run_id': prev_run.id, 'steps': result})


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

    # Transparently decrypt files that were encrypted at rest (.enc suffix).
    if abs_path.suffix == '.enc':
        from flowforge.crypto import decrypt_file_to_stream
        stream    = decrypt_file_to_stream(abs_path)
        real_name = abs_path.stem   # strip the .enc suffix
        mime, _   = mimetypes.guess_type(real_name)
        return send_file(
            stream,
            mimetype=mime or 'application/octet-stream',
            as_attachment=True,
            download_name=real_name,
        )

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
    from datetime import datetime
    run = db.session.get(PipelineRun, str(run_id))
    if not run:
        return jsonify({'error': _NOT_FOUND}), 404
    if run.status not in ('running', 'pending'):
        return jsonify({'error': f'Cannot cancel a run with status {run.status!r}'}), 409
    run.status = 'cancelled'
    run.finished_at = datetime.now(UTC)
    db.session.commit()
    return jsonify({'message': 'Run cancelled', 'run_id': str(run_id)})
