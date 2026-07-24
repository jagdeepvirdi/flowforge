from flowforge.api.pipeline_service import next_run_iso
from flowforge.db.models import Pipeline, PipelineRun, StepRun, WebhookToken


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


def pipeline_dict(p: Pipeline) -> dict:
    return {
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'schedule': p.schedule,
        'next_run': next_run_iso(p.schedule),
        'enabled': p.enabled,
        'timeout_minutes': p.timeout_minutes,
        'on_failure_webhook_url': p.on_failure_webhook_url,
        'project_id': p.project_id,
        'created_at': p.created_at.isoformat() if p.created_at else None,
        'updated_at': p.updated_at.isoformat() if p.updated_at else None,
        'steps': [
            {
                'id':             s.id,
                'step_order':     s.step_order,
                'name':           s.name,
                'step_type':      s.step_type,
                'config':         s.config,
                'on_error':       s.on_error,
                'enabled':        s.enabled,
                'parallel_group': s.parallel_group,
            }
            for s in p.steps
        ],
        'variables': [
            {
                'id': v.id,
                'var_key': v.var_key,
                'var_value': '***' if v.is_secret else v.var_value,
                'is_secret': v.is_secret,
            }
            for v in p.variables
        ],
        'upstream_deps': [
            {'dep_id': d.id, 'pipeline_id': d.upstream_id, 'pipeline_name': d.upstream.name}
            for d in p.upstream_deps
        ],
        'downstream_deps': [
            {'dep_id': d.id, 'pipeline_id': d.downstream_id, 'pipeline_name': d.downstream.name}
            for d in p.downstream_deps
        ],
    }


def webhook_token_dict(t: WebhookToken, *, raw: str | None = None) -> dict:
    d = {
        'id': t.id,
        'pipeline_id': t.pipeline_id,
        'label': t.label,
        'enabled': t.enabled,
        'last_used_at': t.last_used_at.isoformat() if t.last_used_at else None,
        'created_at': t.created_at.isoformat() if t.created_at else None,
    }
    if raw is not None:
        d['token'] = raw   # returned only at creation, never stored
    return d


def pipeline_export_dict(p: Pipeline) -> dict:
    """Shape a pipeline for YAML export/re-import (secrets masked, no DB IDs)."""
    return {
        'name': p.name,
        'description': p.description or '',
        'schedule': p.schedule,
        'enabled': p.enabled,
        'timeout_minutes': p.timeout_minutes,
        'on_failure_webhook_url': p.on_failure_webhook_url,
        'steps': [
            {
                'name': s.name,
                'step_type': s.step_type,
                'step_order': s.step_order,
                'config': dict(s.config),
                'on_error': s.on_error,
                'enabled': s.enabled,
            }
            for s in p.steps
        ],
        'variables': [
            {
                'var_key': v.var_key,
                'var_value': '***' if v.is_secret else v.var_value,
                'is_secret': v.is_secret,
            }
            for v in p.variables
        ],
    }
