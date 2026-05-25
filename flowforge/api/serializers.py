from flowforge.db.models import PipelineRun, StepRun


def run_dict(r: PipelineRun, include_steps: bool = False) -> dict:
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
        result['step_runs'] = [
            step_run_dict(s)
            for s in sorted(r.step_runs, key=lambda s: s.step_order)
        ]
    return result


def step_run_dict(s: StepRun) -> dict:
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
